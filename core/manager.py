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

"""Collection of manager classes."""

__author__ = 'Philipp Engel'
__copyright__ = 'Copyright (c) 2017 Hochschule Neubrandenburg'
__license__ = 'EUPL'

import json
import jsonschema
import logging

from importlib import *
from pathlib import Path
from typing import *

from core.intercom import MQTTMessenger
from core.module import Module
from core.sensor import Sensor
from module.prototype import Prototype


class Manager(object):
    """
    Manager is a container class for the configuration manager, the sensor
    manager, the module manager, and the schema manager.
    """

    def __init__(self):
        self._config_manager = None
        self._sensor_manager = None
        self._module_manager = None
        self._schema_manager = None

    @property
    def config_manager(self) -> Any:
        return self._config_manager

    @property
    def module_manager(self) -> Any:
        return self._module_manager

    @property
    def schema_manager(self) -> Any:
        return self._schema_manager

    @property
    def sensor_manager(self) -> Any:
        return self._sensor_manager

    @config_manager.setter
    def config_manager(self, config_manager):
        self._config_manager = config_manager

    @module_manager.setter
    def module_manager(self, module_manager):
        self._module_manager = module_manager

    @schema_manager.setter
    def schema_manager(self, schema_manager):
        self._schema_manager = schema_manager

    @sensor_manager.setter
    def sensor_manager(self, sensor_manager):
        self._sensor_manager = sensor_manager


class ConfigManager(object):
    """
    ConfigurationManager loads and stores the OpenADMS configuration.
    """

    def __init__(self, path: str, schema_manager):
        """
        Args:
            path: The path to the configuration file.
        """
        self.logger = logging.getLogger('configurationManager')
        self._schema_manager = schema_manager
        self._path = path   # Path to the configuration file.
        self._config = {}   # The actual configuration.

        if self._path:
            self.load_config_from_file(self._path)
        else:
            self.logger.error('No configuration file set')

    def load_config_from_file(self, config_path: str) -> bool:
        """Loads configuration from a JSON file.

        Args:
            config_path: The path to the JSON file.

        Returns:
            True if file has been loaded, False if not.
        """
        if not Path(config_path).exists():
            self.logger.error('Configuration file "{}" not found.'
                              .format(config_path))
            return False

        with open(config_path) as config_file:
            try:
                self._config = json.loads(config_file.read())
                self.logger.info('Loaded configuration file "{}"'
                                 .format(config_path))
            except ValueError as e:
                self.logger.error('Invalid JSON file "{}"'.format(e))
                return False

        return True

    def get(self, key: str) -> Dict[str, Any]:
        """Returns a single configuration.

        Args:
            key: The name of the configuration.

        Returns:
            A dictionary with the configuration.
        """
        return self._config.get(key)

    def get_valid_config(self,
                         schema_name: str,
                         schema_path: str,
                         *args: List[str]) -> Dict[str, Any]:
        """
        Returns the validated configuration of a module. Raises a ValueError
        exception if the configuration is invalid.

        Args:
            schema_name: Name of the JSON schema.
            schema_path: Path to the JSON schema file.
            *args: Key names to the module's configuration.

        Returns:
            A dictionary with the module's configuration.

        Raises:
            ValueError: If module configuration is invalid.
        """
        config = self._config

        # Get module's configuration from dictionary.
        for key in args:
            try:
                config = config[key]
            except AttributeError:
                break

        # Add JSON schema if missing.
        if not self._schema_manager.has_schema(schema_name):
            self._schema_manager.add_schema(schema_name, schema_path)

        # Check whether module's configuration is valid.
        if not self._schema_manager.is_valid(config, schema_name):
            self.logger.error('Configuration "{}" is invalid'
                              .format(schema_name))
            raise ValueError

        return config

    @property
    def config(self) -> Dict[str, Any]:
        return self._config

    @property
    def path(self) -> str:
        return self._path

    @config.setter
    def config(self, config: Dict[str, Any]) -> None:
        self._config = config


class ModuleManager(object):
    """
    ModuleManager loads and manages OpenADMS modules.
    """

    def __init__(self, manager: Manager):
        """
        Args:
            manager: The manager object.
        """
        self.logger = logging.getLogger('moduleManager')
        self._manager = manager
        self._config_manager = manager.config_manager
        self._schema_manager = manager.schema_manager

        self._config = self._config_manager.get('modules')
        self._schema_manager.add_schema('modules', 'core/modules.json')

        self._modules = {}

        for module_name, class_path in self._config.items():
            try:
                self.add(module_name, class_path)
            except Exception as e:
                self.logger.error('Module "{}" not loaded{}'
                                  .format(module_name, ': ' + e))
                continue

    def add(self, module_name: str, class_path: str):
        """Instantiates a worker, instantiates a messenger, and bundles both
        to a module. The module will be added to the modules dictionary.

        Args:
            module_name: Name of the module.
            class_path: Path to the Python class.

        Returns:
            True if module has been added, False if not.

        Raises:
            ValueError: If module file not exists.
        """
        if not self.module_exists(class_path):
            self.logger.error('Module "{}" not found'.format(class_path))
            raise ValueError

        messenger = MQTTMessenger(self._manager, module_name)
        worker = self.get_worker(module_name, class_path)
        self._modules[module_name] = Module(messenger, worker)

    def delete(self, name: str) -> None:
        """Removes a module from the modules dictionary.

        Args:
            name: The name of the module.
        """
        self._modules[name] = None

    def get(self, name: str) -> Module:
        """Returns a specific module.

        Args:
            name: The name of the module.
        """
        return self._modules.get(name)

    def get_modules_list(self) -> List[str]:
        """Returns a list with all names of all modules.

        Returns:
            List of module names.
        """
        return self._modules.keys()

    def get_worker(self, module_name: str, class_path: str) -> Prototype:
        """Loads a Python class from a given path and returns the instance.

        Args:
            module_name: Name of the module.
            class_path: Path to the Python class.

        Returns:
            Instance of Python class or None.
        """
        module_path, class_name = class_path.rsplit('.', 1)
        worker_class = getattr(import_module(module_path),
                               class_name)

        return worker_class(module_name,
                            class_path,
                            self._manager)

    def has_module(self, name: str) -> bool:
        """Returns whether or not module is found.

        Args:
            name: The name of the module.

        Returns:
            True if module is found, False if not.
        """
        if self.modules.get(name):
            return True
        else:
            return False

    def module_exists(self, class_path: str) -> bool:
        """Returns whether or not a OpenADMS module exists in the given file
        path.

        Args:
            class_path: The path to the class.

        Returns:
            True if module exists, False if not.
        """
        module_path, class_name = class_path.rsplit('.', 1)
        file_path = Path(module_path.replace('.', '/') + '.py')

        if not file_path.exists():
            return False

        return True

    def start(self, module_name: str) -> None:
        """Starts a module.

        Args:
            module_name: The name of the module.
        """
        self._modules.get(module_name).start()
        self._modules.get(module_name).start_worker()

    def start_all(self) -> None:
        """Starts all modules."""
        for module_name in self._modules.keys():
            self.start(module_name)

    def stop(self, module_name: str) -> None:
        """Stops a module.

        Args:
            module_name: The name of the module.
        """
        self._modules.get(module_name).stop_worker()

    @property
    def modules(self) -> Dict[str, Module]:
        return self._modules


class SensorManager(object):
    """
    SensorManager stores and manages object of type `Sensor`.
    """

    def __init__(self, config_manager: ConfigManager):
        """
        Args:
            config_manager: The configuration manager.
        """
        self.logger = logging.getLogger('sensorManager')
        self._sensor_config = config_manager.get('sensors')
        self._sensors = {}

        self.load_sensors()

    def load_sensors(self) -> None:
        """Creates the sensors defined in the configuration."""
        if not self._sensor_config:
            self.logger.info('No sensors defined')
            return

        for sensor_name, sensor_config in self._sensor_config.items():
            sensor_obj = Sensor(sensor_name, sensor_config)
            self.add_sensor(sensor_name, sensor_obj)
            self.logger.info('Created sensor "{}"'.format(sensor_name))

    def add_sensor(self, name: str, sensor: Sensor) -> None:
        """Adds a sensor to the sensors dictionary.

        Args:
            name: The name of the sensor.
            sensor: The sensor object.
        """
        self._sensors[name] = sensor

    def delete(self, name: str) -> None:
        """Removes a sensor from the sensors dictionary."""
        self._sensors[name] = None

    def get(self, name: str) -> Sensor:
        """Returns the sensor object with the given name."""
        return self._sensors.get(name)

    def get_sensors_names(self) -> List[str]:
        """Returns a list with all sensor names."""
        return self._sensors.keys()

    @property
    def sensors(self) -> Dict[str, Sensor]:
        return self._sensors


class SchemaManager(object):
    """
    SchemaManager stores JSON schema and validates given data with them.
    """

    def __init__(self):
        self.logger = logging.getLogger('schemaManager')
        self._schema = {}

        self.add_schema('observation', 'observation.json')

    def add_schema(self,
                   data_type: str,
                   path: str,
                   root: str = 'schema') -> bool:
        """Reads a JSON schema file from the given path and stores it in the
        internal dictionary.

        Args:
            data_type: The name of the data type (e.g., 'observation').
            path: The path to the JSON schema file.
            root: The root directory (default: './schema').

        Returns:
            True if schema has been added, False if not.
        """
        schema_path = Path(root, path)

        if not schema_path.exists():
            self.logger.error('Schema file "{}" not found.'
                              .format(schema_path))
            return False

        with open(str(schema_path), encoding='utf-8') as data_file:
            try:
                schema = json.loads(data_file.read())
                jsonschema.Draft4Validator.check_schema(schema)

                self._schema[data_type] = schema
                self.logger.debug('Loaded schema "{}"'
                                  .format(data_type))
            except json.JSONDecodeError:
                self.logger.error('Invalid JSON file "{}"'
                                  .format(schema_path))
                return False
            except jsonschema.SchemaError:
                self.logger.error('Invalid JSON schema "{}"'
                                  .format(schema_path))
                return False

        return True

    def get_schema_path(self, class_path: str) -> Path:
        """Uses the class path of a module to generate the path to the
        configuration schema file.

        For instance, the given class path `module.schedule.Scheduler` will be
        converted to the file path `module/schedule/scheduler.json`.

        Args:
            class_path: The class path of a module.

        Returns:
            The path to the JSON schema of the module's configuration.
        """
        return Path(class_path.replace('.', '/').lower() + '.json')

    def has_schema(self, name: str) -> bool:
        """Returns whether or not a JSON schema for the given name exists.

        Args:
            name: Name of the schema (e.g., 'observation').

        Returns:
            True if schema exists, False if not.
        """
        if self._schema.get(name):
            return True
        else:
            return False

    def is_valid(self, data: Dict, schema_name: str) -> bool:
        """Validates data with JSON schema and returns result.

        Args:
            data: The data.
            schema_name: The name of the schema used for validation.

        Returns:
            True if data is valid, False if not.
        """
        if not self.has_schema(schema_name):
            self.logger.warning('JSON schema "{}" not found'
                                .format(schema_name))
            return False

        try:
            schema = self._schema.get(schema_name)
            jsonschema.validate(data, schema)
        except jsonschema.ValidationError:
            return False

        return True
