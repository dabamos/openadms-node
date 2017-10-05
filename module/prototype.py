#!/usr/bin/env python3.6

"""Prototype class which can be used as a blueprint for other OpenADMS
modules."""

__author__ = 'Philipp Engel'
__copyright__ = 'Copyright (c) 2017 Hochschule Neubrandenburg'
__license__ = 'EUPL'

import json
import logging

from typing import *

from core.observation import Observation


class Prototype(object):
    """
    Prototype is used as a blueprint for OpenADMS workers.
    """

    def __init__(self, module_name: str, module_type: str, manager: Any):
        """
        Args:
            module_name: The name of the module.
            module_type: The type of the module.
            manager: The manager objects.
        """
        self.logger = logging.getLogger(module_name)

        self._name = module_name  # Module name, e.g., 'com5'.
        self._type = module_type  # Module type, e.g., 'module.port.SerialPort'.

        self._config_manager = manager.config_manager
        self._module_manager = manager.module_manager
        self._node_manager = manager.node_manager
        self._project_manager = manager.project_manager
        self._sensor_manager = manager.sensor_manager
        self._schema_manager = manager.schema_manager

        self._uplink = None
        self._is_running = False

        # A dictionary of the various payload data types and their respective
        # callback functions. Further callback functions can be added with the
        # `add_handler()` method.
        self._handlers = {
            'observation': self.do_handle_observation,
            'service': self.do_handle_service
        }

    def add_handler(self,
                    data_type: str,
                    func: Callable[[Dict, Dict], None]) -> None:
        """Registers a callback function for handling of messages.

        Args:
            data_type: Name of the data type (observation, service, ...).
            func: Callback function for handling the message.
        """
        self._handlers[data_type] = func

    def do_handle_observation(self, header: Dict, payload: Dict) -> None:
        """Handles an observation by forwarding it to the processing method and
        prepares the result for publishing."""
        obs = Observation(payload)

        if self._is_running:
            obs = self.process_observation(Observation(payload))

        if obs:
            self.publish_observation(obs)

    def do_handle_service(self, header: Dict, payload: Dict) -> None:
        """Processes service messages.

        Args:
            header: The message header.
            payload: The message payload.
        """
        sender = header.get('from', '?')
        action = payload.get('action')

        if action is 'stop':
            self._is_running = False
            self.logger.debug('Stopped module "{}" by call from "{}"'
                              .format(self._name, sender))
        elif action is 'start':
            self._is_running = True
            self.logger.debug('Started module "{}" by call from "{}"'
                              .format(self._name, sender))

    def handle(self, message: List[Dict]) -> None:
        """Processes messages by calling callback functions for data
        handling.

        Args:
            message: Header and payload of the message, both Dict.
        """
        if not self.is_sequence(message) or len(message) < 2:
            self.logger.warning('Received message is invalid')
            return

        header = message[0]
        payload = message[1]

        if not header or not payload:
            self.logger.warning('Received data is corrupted')
            return

        # Get payload type.
        payload_type = header.get('type')

        if not payload_type:
            self.logger.error('No payload type defined')
            return

        # Validate payload.
        if not self.is_valid(payload, payload_type):
            self.logger.error('Payload of type "{}" is invalid'
                              .format(payload_type))
            return

        # Send payload to specific handler.
        handler_func = self._handlers.get(payload_type)

        if not handler_func:
            self.logger.warning('No handler found for payload type "{}"'
                                .format(payload_type))
            return

        handler_func(header, payload)

    def get_config(self, *args):
        """Returns the validated configuration of the module. If no JSON schema
        is available, the function just returns an unchecked configuration.

        Args:
            *args: Key names to the configuration in the dictionary.

        Returns:
            A dictionary with the module's configuration.
        """
        # Add the JSON schema to the Schema Manager.
        schema_path = self._schema_manager.get_schema_path(self._type)
        self._schema_manager.add_schema(self._type, schema_path)

        # Return a valid configuration for the module or raise an exception.
        return self._config_manager.get_valid_config(self._type, *args)

    def is_sequence(self, arg: Any) -> bool:
        """Checks whether the argument is a list/a tuple or not.

        Returns:
            True if argument is a sequence, False if not."""
        return (not hasattr(arg, 'strip') and
                hasattr(arg, '__getitem__') or
                hasattr(arg, '__iter__'))

    def is_valid(self, data: Dict, data_type: str) -> bool:
        """Returns whether or not given data is valid by checking against the
        JSON schema.

        Args:
            data: The data.
            data_type: The name of the data type.

        Returns:
            True if data is valid, False if not.
        """
        return self._schema_manager.is_valid(data, data_type)

    def process_observation(self, obs: Observation) -> Observation:
        """Processes an observation object. Will be overridden by actual
        worker.

        Args:
            obs: The observation object.

        Returns:
            The processed observation object.
        """
        return obs

    def publish(self, target: str, header: Dict, payload: Dict) -> None:
        """Appends header and payload to a list, converts the list to a JSON
        string and sends it to the designated target by using the callback
        function `_uplink()`. The JSON string has the format:

            [ { <header> }, { <payload> } ].

        Args:
            target: The name of the target.
            header: The header of the message.
            payload: The payload of the message.
        """
        if not self._uplink:
            self.logger.error('No uplink defined for module "{}"'
                              .format(self._name))
            return

        try:
            message = json.dumps([header, payload])
            self._uplink(target, message)
        except TypeError as e:
            self.logger.error('Message could not be published '
                              '(header or payload invalid): {}'.format(e))

    def publish_observation(self, obs: Observation) -> None:
        """Prepares the observation for publishing and forwards it to the
        messenger.

        Args:
            obs: Observation object.
        """
        receivers = obs.get('receivers')
        index = obs.get('nextReceiver')

        # No receivers defined.
        if len(receivers) == 0:
            logging.debug('No receivers defined in observation "{}" '
                          'of target "{}"'.format(obs.get('name'),
                                                  obs.get('target')))
            return

        # No index defined.
        if (index is None) or (index < 0):
            self.logger.warning('Next receiver of observation "{}" with target '
                                '"{}" not defined'.format(obs.get('name'),
                                                          obs.get('target')))
            return

        # Receivers list has been processed and observation is finished.
        if index >= len(receivers):
            self.logger.info('Observation "{}" of target "{}" has been '
                             'finished'.format(obs.get('name'),
                                               obs.get('target')))
            return

        # Name of the sending module.
        sender = receivers[index - 1]

        # Increase the receivers index.
        next_receiver = receivers[index]
        obs.set('nextReceiver', index + 1)

        # Create header and payload.
        header = {
            'from': sender,
            'type': 'observation'
        }

        payload = obs.data

        # Send the observation to the next module.
        self.publish(next_receiver, header, payload)

    def start(self) -> None:
        """Starts the worker."""
        if self._is_running:
            return

        self.logger.debug('Starting worker "{}"'.format(self._name))
        self._is_running = True

    def stop(self) -> None:
        """Stops the worker."""
        if not self._is_running:
            return

        self.logger.debug('Stopping worker "{}"'.format(self._name))
        self._is_running = False

    @property
    def is_running(self) -> bool:
        return self._is_running

    @property
    def name(self) -> str:
        return self._name

    @property
    def type(self) -> str:
        return self._type

    @property
    def uplink(self) -> Callable[[str, str], None]:
        return self._uplink

    @type.setter
    def type(self, type: str) -> None:
        self._type = type

    @uplink.setter
    def uplink(self, uplink: Callable[[str, str], None]) -> None:
        self._uplink = uplink
