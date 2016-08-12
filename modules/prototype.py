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
import threading
import time

from abc import ABCMeta, abstractmethod

from core import observation
from core import intercom

logger = logging.getLogger('openadms')


class Prototype(object, metaclass=ABCMeta):

    """
    Used as a prototype for other modules.
    """

    def __init__(self, name, config_manager, sensor_manager):
        self._name = name
        self._config_manager = config_manager
        self._sensor_manager = sensor_manager

        self._messenger = intercom.MQTTMessenger('localhost')
        self._messenger.subscribe('openadms/{}'.format(self._name))
        self._messenger.register(self.retrieve)
        self._messenger.connect()

    @abstractmethod
    def action(self, *args):
        """Abstract function that does the action of a module.

        Args:
            *args: Variable length argument list.
        """
        pass

    def publish(self, obs):
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

        # Receivers list has been processed.
        if index >= len(receivers):
            logger.debug('Observation "{}" has been finished'.format(name))
            return

        receiver = receivers[index]
        index = index + 1
        obs.set('NextReceiver', index)

        target = 'openadms/{}'.format(receiver)
        payload = obs.to_json()

        self._messenger.publish(target, payload)

    def retrieve(self, msg):
        data = json.loads(msg)
        obs = observation.Observation(data)
        obs = self.action(obs)

        if obs is not None:
            self.publish(obs)

    @property
    def name(self):
        return self._name

    @property
    def config_manager(self):
        return self._config_manager

    @property
    def sensor_manager(self):
        return self._sensor_manager
