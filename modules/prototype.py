#!/usr/bin/env python3
"""
Copyright (c) 2016 Hochschule Neubrandenburg.

Licenced under the EUPL, Version 1.1 or - as soon they will be approved
by the European Commission - subsequent versions of the EUPL (the
"Licence");

You may not use this work except in compliance with the Licence.

You may obtain a copy of the Licence at:

    https://joinup.ec.europa.eu/community/eupl/og_page/eupl

Unless required by applicable law or agreed to in writing, software
distributed under the Licence is distributed on an "AS IS" basis,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the Licence for the specific language governing permissions and
limitations under the Licence.
"""

import json
import logging
import queue
import threading

from core.observation import Observation

"""Collects prototype classes which can be used as blueprints for other
OpenADMS modules."""


class Module(threading.Thread):
    """
    Module bundles a worker with a messenger and manages the communication
    between them.
    """

    def __init__(self, messenger, worker):
        threading.Thread.__init__(self, name=worker.name)
        self.logger = logging.getLogger(worker.name)
        self.daemon = True

        self._messenger = messenger
        self._worker = worker

        self._inbox = queue.Queue()
        self._topic = self._messenger.topic

        # Set the callback functions of the messenger and the worker.
        self._messenger.downlink = self.retrieve
        self._worker.uplink = self.publish

        # Subscribe to the worker's name.
        self._messenger.subscribe(self._topic + '/' + worker.name)

    def publish(self, target, message):
        """Sends an `Observation` object to the next receiver by using the
        messenger."""
        target_path = '{}/{}'.format(self._topic, target)
        self._messenger.publish(target_path, message)

    def retrieve(self, message):
        """Callback function for the messenger. New data from the message broker
        lands here."""
        self._inbox.put(message)

    def run(self):
        """Checks the inbox for new messages and calls the `handle()` method of
        the worker for further processing. Runs within a thread."""
        self.logger.debug('Connecting module "{}" to {}:{} ...'
                          .format(self._worker.name,
                                  self._messenger.host,
                                  self._messenger.port))

        self._messenger.connect()

        while True:
            message = self._inbox.get()     # Blocking I/O.
            self._worker.handle(message)    # Fire and forget.

        self._messenger.disconnect()

    @property
    def messenger(self):
        return self._messenger

    @property
    def worker(self):
        return self._worker

    @messenger.setter
    def messenger(self, messenger):
        self._messenger = messenger

    @worker.setter
    def worker(self, worker):
        self._worker = worker


class Prototype(object):
    """
    Prototype is used as a blueprint for OpenADMS workers.
    """

    def __init__(self, name, config_manager, sensor_manager):
        self._name = name
        self.logger = logging.getLogger(self.name)

        self._config_manager = config_manager
        self._sensor_manager = sensor_manager

        self._uplink = None
        self._is_paused = False

        # A dictionary of the various payload data types and their respective
        # callback functions.  Further callback functions can be added with the
        # `add_handler()` method.
        self._handlers = {
            'observation': self.handle_observation,
            'service': self.handle_service
        }

    def add_handler(self, name, func):
        """Registers a callback function for handling of messages."""
        self._handlers[name] = func

    def handle(self, message):
        """Processes messages by calling callback functions for data
        handling."""
        if not self.is_sequence(message) or len(message) < 2:
            self.logger.warning('{}: received message is invalid'
                                .format(self._name))
            return

        header = message[0]
        payload = message[1]

        if not header or not payload:
            self.logger.warning('{}: received data is corrupted'
                                .format(self._name))
            return

        payload_type = header.get('type')

        if not payload_type:
            self.logger.error('{}: no payload type defined'.format(self._name))
            return

        handler_func = self._handlers.get(payload_type)

        if not handler_func:
            self.logger.warning('{}: no handler found for payload type "{}"'
                                .format(self._name, payload_type))
            return

        handler_func(header, payload)

    def handle_observation(self, header, payload):
        """Handles an observation by forwarding it to the processing method and
        prepares the result for publishing."""
        obs = Observation(payload)
        obs = self.process_observation(obs)

        if not obs:
            return

        self.publish_observation(obs)

    def handle_service(self, header, payload):
        """Processes service messages."""
        # If `pause` is set, change status of the worker accordingly.
        sender = header.get('from')
        pause = payload.get('pause')

        if pause is None or pause == self._is_paused:
            return

        self._is_paused = pause

        if pause:
            self.logger.info('Paused module "{}" by call from "{}"'
                             .format(self._name, sender))
        else:
            self.logger.info('Started module "{}" by call from "{}"'
                             .format(self._name, sender))

    def is_sequence(self, arg):
        """Checks whether the argument is a list/a tuple or not."""
        return (not hasattr(arg, 'strip') and
                hasattr(arg, '__getitem__') or
                hasattr(arg, '__iter__'))

    def process_observation(self, obs):
        pass

    def process_service(self, service):
        pass

    def publish_observation(self, obs):
        """Prepares the observation for publishing and forwards it to the
        messenger."""
        receivers = obs.get('receivers')
        index = obs.get('nextReceiver')

        # No receivers defined.
        if len(receivers) == 0:
            logging.debug('No receivers defined in observation "{}" '
                          'with ID "{}"'.format(obs.get('name'),
                                                obs.get('id')))
            return

        # No index defined.
        if (index is None) or (index < 0):
            self.logger.warning('Next receiver of observation "{}" with ID '
                                '"{}" not defined'.format(obs.get('name'),
                                                          obs.get('id')))
            return

        # Receivers list has been processed and observation is finished.
        if index >= len(receivers):
            self.logger.debug('Observation "{}" with ID "{}" has been finished'
                              .format(obs.get('name'),
                                      obs.get('id')))
            return

        # Name of the sending module.
        sender = receivers[index - 1]

        # Increase the receivers index.
        next_receiver = receivers[index]
        index += 1
        obs.set('nextReceiver', index)

        # Create header and payload.
        header = {
            'from': sender,
            'type': 'observation'
        }

        payload = obs.data

        # Send the observation to the next module.
        self.publish(next_receiver, header, payload)

    def publish_service(self, service):
        pass

    def publish(self, target, header, payload):
        """Appends header and payload to a list, converts the list to a JSON
        string and sends it to the designated target by using the callback
        function `_uplink()`. The JSON string has the format:

            [ { <header> }, { <payload> } ].

        Args:
            target (str): The name of the target.
            header (Dict): The header of the message.
            payload (Dict): The payload of the message.
        """
        if not self._uplink:
            self.logger.error('No uplink defined for module "{}"'
                              .format(self._name))
            return

        try:
            message = json.dumps([header, payload])
            self._uplink(target, message)
        except TypeError:
            self.logger.error('Can\'t publish message '
                              '(header or payload invalid)')

    @property
    def name(self):
        return self._name

    @property
    def config_manager(self):
        return self._config_manager

    @property
    def is_paused(self):
        return self._is_paused

    @property
    def sensor_manager(self):
        return self._sensor_manager

    @property
    def uplink(self):
        return self._uplink

    @uplink.setter
    def uplink(self, uplink):
        self._uplink = uplink
