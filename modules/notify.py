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

"""Module for virtual sensors."""

logger = logging.getLogger('openadms')


class Alarm(prototype.Prototype):

    def __init__(self, name, config_manager, sensor_manager):
        prototype.Prototype.__init__(self, name, config_manager,
                                     sensor_manager)
        config = config_manager.config.get('Alarm')

        self._queue = queue.Queue(-1)
        qh = logging.handlers.QueueHandler(self._queue)
        qh.setLevel(logging.WARNING)
        logger.addHandler(qh)

        self._alarm_handlers = []

        project_name = config_manager.config.get('Project').get('Name')
        is_sms_handler_enabled = config.get('SMSHandlerEnabled')
        handlers_config = config.get('Handlers')

        if is_sms_handler_enabled:
            sh_config = handlers_config.get('SMSHandler')
            log_level = sh_config.get('LogLevel')
            host = sh_config.get('Host')
            port = sh_config.get('Port')
            phone_numbers = sh_config.get('PhoneNumbers')
            template = sh_config.get('Template')

            sms = SMSHandler(log_level, host, port, phone_numbers, template)
            sms.add_var('project', project_name)
            self._alarm_handlers.append(sms)

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

    def __init__(self):
        self._msg_vars = {}

    def add_var(self, key, value):
        self._msg_vars['{' + key + '}'] = value

    @abstractmethod
    def handle(self, record):
        pass


class SMSHandler(AlarmHandler):

    def __init__(self, log_level, host, port, phone_numbers, template):
        AlarmHandler.__init__(self)
        self._log_level = log_level
        self._host = host
        self._port = port
        self._phone_numbers = phone_numbers
        self._template = template

    def handle(self, record):
        if record.levelname != self._log_level.upper():
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
