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

from core.observation import Observation

"""Collects prototype classes which can be used as blueprints for other
OpenADMS modules."""

logger = logging.getLogger('openadms')


class Module(threading.Thread):

    """
    Module bundles a worker with a messenger and orchestrates the communication
    between them.
    """

    def __init__(self, messenger, worker):
        threading.Thread.__init__(self, name=worker.name)
        self.daemon = True

        self._messenger = messenger
        self._worker = worker

        self._inbox = queue.Queue()
        self._topic = self._messenger.topic

        # Set the callback functions of the messenger and the worker.
        self._messenger.uplink = self._retrieve
        self._worker.uplink = self._publish

        # Subscribe to the worker's name.
        self._messenger.subscribe(self._topic + '/' + worker.name)

    def _publish(self, obs):
        """Sends an `Observation` to the next receiver by using the
        messenger."""
        if not self._messenger:
            logger.warning('No messenger defined for module "{}"'
                           .format(self._name))
            return

        receivers = obs.get('Receivers')
        index = obs.get('NextReceiver')

        # No receivers defined.
        if len(receivers) == 0:
            logging.debug('No receivers defined in observation "{}" '
                          'with ID "{}"'.format(obs.get('Name'),
                                                obs.get('ID')))
            return

        # No index defined.
        if (index is None) or (index < 0):
            logger.warning('Next receiver of observation "{}" with ID "{}" not '
                           'defined'.format(obs.get('Name'),
                                            obs.get('ID')))
            return

        # Receivers list has been processed and observation is finished.
        if index >= len(receivers):
            logger.debug('Observation "{}" with ID "{}" has been finished'
                         .format(obs.get('Name'),
                                 obs.get('ID')))
            return

        # Send the observation to the next module.
        receiver = receivers[index]
        index += 1
        obs.set('NextReceiver', index)

        target = '{}/{}'.format(self._topic, receiver)
        payload = obs.to_json()

        self._messenger.publish(target, payload)

    def _retrieve(self, data):
        """Callback function for the messenger. New data from the message broker
        lands here."""
        obs = Observation(data)
        self._inbox.put(obs)

    def run(self):
        """Checks the inbox for new messages and calls the `action()` for
        further processing. Runs within a thread."""
        logger.debug('Connecting module "{}" to {}:{} ...'
                     .format(self._worker.name,
                             self._messenger.host,
                             self._messenger.port))

        self._messenger.connect()

        while True:
            if self._inbox.empty():
                time.sleep(0.01)
                continue

            obs = self._worker.action(self._inbox.get())

            if obs is not None:
                self._publish(obs)

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


class Prototype():

    """
    Prototype is used as a blueprint for OpenADMS workers.
    """

    __metaclass__ = ABCMeta

    def __init__(self, name, config_manager, sensor_manager):
        threading.Thread.__init__(self, name=name)

        self._config_manager = config_manager
        self._sensor_manager = sensor_manager

        self._uplink = None

    @abstractmethod
    def action(self, *args):
        """Abstract function that does the action of a module.

        Args:
            *args: Variable length argument list.
        """
        pass

    def publish(self, obs):
        """Sends `Observation` to the callback function of the parent module.

        Args:
            obs (Observation): Observation object.
        """
        if self._uplink:
            self._uplink(obs)

    @property
    def name(self):
        return self._name

    @property
    def config_manager(self):
        return self._config_manager

    @property
    def sensor_manager(self):
        return self._sensor_manager

    @property
    def uplink(self):
        return self._uplink

    @uplink.setter
    def uplink(self, uplink):
        self._uplink = uplink