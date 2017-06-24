#!/usr/bin/env python3
"""
Copyright (c) 2017 Hochschule Neubrandenburg.

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

"""Prototype class which can be used as a blueprint for other OpenADMS
modules."""

__author__ = 'Philipp Engel'
__copyright__ = 'Copyright (c) 2017 Hochschule Neubrandenburg'
__license__ = 'EUPL'

import json
import jsonschema
import pathlib

from core.manager import *
from core.observation import Observation


class Prototype(object):
    """
    Prototype is used as a blueprint for OpenADMS workers.
    """

    def __init__(self, name, type, manager):
        self.logger = logging.getLogger(name)

        self._name = name   # Module name, e.g., 'serialPort'.
        self._type = type   # Class path, e.g., 'module.port.SerialPort'.

        self._config_manager = manager.config_manager
        self._module_manager = manager.module_manager
        self._sensor_manager = manager.sensor_manager

        self._uplink = None
        self._is_running = False

        # A dictionary of the various payload data types and their respective
        # callback functions.  Further callback functions can be added with the
        # `add_handler()` method.
        self._handlers = {
            'observation': self.do_handle_observation,
            'service': self.do_handle_service
        }

        self._schema_root = pathlib.Path('schema')
        self._schema = {}

        self.add_schema('observation', 'observation.json')

    def add_handler(self,
                    data_type: str,
                    func: Callable[[Dict, Dict], None]) -> None:
        """Registers a callback function for handling of messages.

        Args:
            data_type (str): Name of the data type (observation, service, ...).
            func (Callable): Callback function for handling the message.
        """
        self._handlers[data_type] = func

    def add_schema(self, data_type: str, path: str) -> None:
        schema = None
        schema_path = self._schema_root / path

        with open(schema_path, encoding='utf-8') as data_file:
            try:
                schema = json.loads(data_file.read())
                jsonschema.Draft4Validator.check_schema(schema)

                self._schema[data_type] = schema
                self.logger.debug('Loaded JSON schema "{}" from "{}"'
                                  .format(data_type, schema_path))
            except json.JSONDecodeError:
                self.logger.error('Invalid JSON file "{}"'
                                  .format(schema_path))
                return
            except jsonschema.SchemaError:
                self.logger.error('Invalid JSON schema "{}"'
                                  .format(schema_path))
                return

    def do_handle_observation(self, header: Dict, payload: Dict) -> None:
        """Handles an observation by forwarding it to the processing method and
        prepares the result for publishing."""
        obs = Observation(payload)

        if self._is_running:
            obs = self.process_observation(Observation(payload))

        if obs:
            self.publish_observation(obs)

    def do_handle_service(self, header: Dict, payload: Dict) -> None:
        """Processes service messages."""
        sender = header.get('from', '?')
        action = payload.get('action')

        if action is 'pause':
            self._is_running = False
            self.logger.debug('Paused module "{}" by call from "{}"'
                              .format(self._name, sender))
        elif action is 'start':
            self._is_running = True
            self.logger.debug('Started module "{}" by call from "{}"'
                              .format(self._name, sender))

    def handle(self, message: List[Dict]) -> None:
        """Processes messages by calling callback functions for data
        handling.

        Args:
            message (List): Header and payload of the message, both Dict.
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
            self.logger.error('{}: no payload type defined'.format(self._name))
            return

        # Validate payload.
        if self.has_validator(payload_type):
            if not self.validate(payload, payload_type):
                self.logger.error('Data of type "{}" is not valid'
                                  .format(payload_type))
        else:
            self.logger.warning('No validator found for type "{}"'
                                .format(payload_type))

        # Send payload to specific handler.
        handler_func = self._handlers.get(payload_type)

        if not handler_func:
            self.logger.warning('{}: no handler found for payload type "{}"'
                                .format(self._name, payload_type))
            return

        handler_func(header, payload)

    def has_validator(self, data_type: str) -> bool:
        """Returns whether or not a JSON validator for the given data type is
        available.

        Args:
            data_type (str): Type of data (e.g., 'observation').
        """
        if self._schema.get(data_type):
            return True
        else:
            return False

    def is_sequence(self, arg: Any) -> bool:
        """Checks whether the argument is a list/a tuple or not."""
        return (not hasattr(arg, 'strip') and
                hasattr(arg, '__getitem__') or
                hasattr(arg, '__iter__'))

    def process_observation(self, obs: Type[Observation]) -> Observation:
        # Will be overwritten by worker.
        pass

    def publish(self, target: str, header: Dict, payload: Dict) -> None:
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

    def publish_observation(self, obs: Type[Observation]) -> None:
        """Prepares the observation for publishing and forwards it to the
        messenger.

        Args:
            obs (Observation): Observation object.

        Returns:
            Observation object.
        """
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
        obs.set('nextReceiver', index + 1)

        # Create header and payload.
        header = {
            'from': sender,
            'type': 'observation'
        }

        payload = obs.data

        # Send the observation to the next module.
        self.publish(next_receiver, header, payload)

    def start(self):
        self.logger.debug('Starting worker "{}" ...'
                          .format(self._name))
        self._is_running = True

    def stop(self):
        self.logger.debug('Stopping worker "{}" ...'
                          .format(self._name))
        self._is_running = False

    def validate(self, data: Dict, data_type: str) -> bool:
        schema = self._schema.get(data_type)

        if not schema:
            self.logger.warning('JSON schema "{}" not found'
                                .format(data_type))
            return False

        try:
            jsonschema.validate(data, schema)
        except jsonschema.ValidationError as e:
            self.logger.warning(e)
            return False

        return True

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
