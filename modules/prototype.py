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

import json
import logging
import paho.mqtt.client as mqtt
import queue
import threading
import time

from abc import ABCMeta, abstractmethod

from core import observation
from core import intercom

"""Collects prototype classes which can be used as blueprints for other
OpenADMS modules."""

logger = logging.getLogger('openadms')


class Prototype(threading.Thread):

    """
    Prototype is used as a blueprint for other modules.
    """

    __metaclass__ = ABCMeta

    def __init__(self, name, config_manager, sensor_manager):
        threading.Thread.__init__(self, name=name)

        self._config_manager = config_manager
        self._sensor_manager = sensor_manager
        self._inbox = queue.Queue()

        self._host = 'localhost'
        self._port = 1883
        self._messenger = intercom.MQTTMessenger(self._host, self._port)
        self._topic = 'OpenADMS'

    @abstractmethod
    def action(self, *args):
        """Abstract function that does the action of a module.

        Args:
            *args: Variable length argument list.
        """
        pass

    def publish(self, obs):
        """Checks observation for the next receiver and sends it to the message
        broker.

        Args:
            obs (Observation): Observation object.
        """
        name = obs.get('Name')
        receivers = obs.get('Receivers')
        index = obs.get('NextReceiver')

        # No receivers defined.
        if len(receivers) == 0:
            logging.debug('No receivers defined in observation "{}"'
                          .format(name))
            return

        # No index defined.
        if (index is None) or (index < 0):
            logger.warning('Next receiver of observation "{}" not '
                           'defined'.format(name))
            return

        # Receivers list has been processed and observation is finished.
        if index >= len(receivers):
            logger.debug('Observation "{}" has been finished'.format(name))
            return

        # Send the observation to the next module.
        receiver = receivers[index]
        index = index + 1
        obs.set('NextReceiver', index)

        target = '{}/{}'.format(self._topic, receiver)
        payload = obs.to_json()
        self._messenger.publish(target, payload)

    def retrieve(self, msg):
        """The callback function which is called by the intercom client every
        time a new message has been received.

        Args:
            msg (str): Message received from the message broker.
        """
        data = json.loads(msg)
        obs = observation.Observation(data)
        self._inbox.put(obs)

    def run(self):
        """Checks the inbox on new messages and calls the `action()` for
        further processing. Runs within a thread."""
        self._messenger.subscribe('{}/{}'.format(self._topic, self._name))
        self._messenger.register(self.retrieve)

        logger.debug('Connecting module "{}" to {}:{} ...'.format(self._name,
                                                                  self._host,
                                                                  self._port))
        self._messenger.connect()

        while True:
            if self._inbox.empty():
                time.sleep(0.01)
                continue

            obs = self.action(self._inbox.get())

            if obs is not None:
                self.publish(obs)

        self._messenger.disconnect()

    @property
    def name(self):
        return self._name

    @property
    def config_manager(self):
        return self._config_manager

    @property
    def sensor_manager(self):
        return self._sensor_manager
