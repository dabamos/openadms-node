#!/usr/bin/env python3
"""
Copyright (c) 2016 Hochschule Neubrandenburg.

Licensed under the EUPL, Version 1.1 or - as soon they will be approved
by the European Commission - subsequent versions of the EUPL (the
"Licence");

You may not use this work except in compliance with the Licence.

You may obtain a copy of the Licence at:

    http://ec.europa.eu/idabc/eupl

Unless required by applicable law or agreed to in writing, software
distributed under the Licence is distributed on an "AS IS" basis,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the Licence for the specific language governing permissions and
limitations under the Licence.
"""

import logging
import queue
import socket
import threading
import time

from abc import ABCMeta, abstractmethod

from modules import prototype

"""Module for alarming."""

logger = logging.getLogger('openadms')


class Alarm(prototype.Prototype):

    def __init__(self, name, config_manager, sensor_manager):
        prototype.Prototype.__init__(self, name, config_manager,
                                     sensor_manager)
        config = config_manager.config.get(self._name)

        self._queue = queue.Queue(-1)
        self._alarm_handlers = []

        # Add logging handler to the logger.
        qh = logging.handlers.QueueHandler(self._queue)
        qh.setLevel(logging.WARNING)    # Get WARNING, ERROR, and CRITICAL.
        logger.addHandler(qh)

        # Add the alarm handlers to the alarm handlers list.
        handlers = self._config.get('Handlers')

        for handler in handlers:
            h_class = vars().get(handler)

            if h_class:
                h = h_class(handlers.get(handler))
                self._alarm_handlers.append(h)
            else:
                logger.warning('Alarm handler "{}" not found'.format(handler))

        # Check the logging queue continuously for messages and proceed them to
        # the alarm handlers.
        self._thread = threading.Thread(target=self._process)
        self._thread.daemon = True
        self._thread.start()

    def action(self, obs):
        return obs

    def _process(self):
        while True:
            if not self._queue.empty():
                record = self._queue.get()
                for alarm_handler in self._alarm_handlers:
                    alarm_handler.handle(record)

            time.sleep(0.1)


class AlarmHandler(object):

    __metaclass__ = ABCMeta

    def __init__(self, config):
        self._config = config
        self._msg_vars = {}

    def add_var(self, key, value):
        self._msg_vars['{' + key + '}'] = value

    @abstractmethod
    def handle(self, record):
        pass


class ShortMessageAlarmHandler(AlarmHandler):

    def __init__(self, config):
        AlarmHandler.__init__(self, config)
        self._config = config

        self._log_levels = config.get('LogLevels')
        self._host = config.get('Host')
        self._port = config.get('Port')
        self._phone_numbers = config.get('PhoneNumbers')
        self._template = config.get('Template')

        # Add the current project name to the dict of message variables.
        project_name = self._config_manager.get('Project').get('Name')
        self.add_var('project', project_name)

    def handle(self, record):
        if record.levelname not in self._log_levels.upper():
            return

        self.add_var('asctime', record.asctime)
        self.add_var('level', record.levelname)
        self.add_var('msg', record.message)

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.connect((self._host, self._port))

            for number in self._phone_numbers:
                text = self._template
                self.add_var('number', number)

                for key, value in self._msg_vars.items():
                    text = text.replace(key, value)

                sock.send(text.encode())
                time.sleep(1.0)


class MailAlarmHandler(AlarmHandler):

    def __init__(self, config_manager):
        AlarmHandler.__init__(self, config_manager)
        config = config_manager.config.get('Alarm').get('SocketAlarmHandler')
