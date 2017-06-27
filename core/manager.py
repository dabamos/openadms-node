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
    def config_manager(self):
        return self._config_manager

    @property
    def module_manager(self):
        return self._module_manager

    @property
    def schema_manager(self):
        return self._schema_manager

    @property
    def sensor_manager(self):
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

    def __init__(self, path: str):
        self.logger = logging.getLogger('configurationManager')
        self._config = {}   # The actual configuration.
        self._path = path   # Path to the configuration file.

        if self._path:
            self.load(self._path)
        else:
            self.logger.error('No configuration file set')

    def load(self, config_path: str) -> bool:
        """Loads configuration from JSON file."""
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

    def dump(self) -> None:
        """Dumps the configuration to stdout."""
        encoded = json.dumps(self._config, sort_keys=True, indent=4)
        print(encoded)

    def get(self, key: str) -> Any:
        return self._config.get(key)

    @property
    def config(self) -> Dict:
        return self._config

    @property
    def path(self) -> str:
        return self._path

    @config.setter
    def config(self, config: Dict) -> None:
        self._config = config


class ModuleManager(object):
    """
    ModuleManager loads and manages OpenADMS module.
    """

    def __init__(self, manager: Type[Manager]):
        self.logger = logging.getLogger('moduleManager')

        self._manager = manager
        self._manager.module_manager = self

        self._config = self._manager.config_manager.get('modules')
        self._modules = {}

        for module_name, class_path in self._config.items():
            if not self.add(module_name, class_path):
                self.logger.error('Module "{}" not loaded'.format(module_name))
                continue

            self.start(module_name)

    def add(self, module_name: str, class_path: str) -> bool:
        """Instantiates a worker, instantiates a messenger, and bundles both
        to a module. The module will be added to the modules dictionary.

        Args:
            module_name (str): Name of the module.
            class_path (str): Path to the Python class.

        Returns:
            True of module has been added, False if not.
        """
        self.logger.info('Loading module "{}"'.format(module_name))
        messenger = MQTTMessenger(self._manager.config_manager)
        worker = None

        if not self.module_exists(class_path):
            self.logger.error('Module "{}" not found'.format(class_path))
            return False

        worker = self.get_worker(module_name, class_path)

        if not worker:
            return False

        if not worker.has_valid_configuration():
            self.logger.error('Configuration of module "{}" is invalid'
                              .format(module_name))
            return False

        self._modules[module_name] = Module(messenger, worker)
        return True

    def delete(self, name: str) -> None:
        """Removes a module from the modules dictionary.

        Args:
            name (str): The name of the module.
        """
        self._modules[name] = None

    def get(self, name: str) -> Type[Module]:
        """Returns a specific module.

        Args:
            name (str): The name of the module.
        """
        return self._modules.get(name)

    def get_modules_list(self) -> List[str]:
        """Returns a list with all names of all modules.

        Returns:
            List of module names.
        """
        return self._modules.keys()

    def get_root_dir(self) -> Type[Path]:
        """Returns the root directory of OpenADMS.

        Returns:
            Path object.
        """
        return Path(__file__).parent.parent

    def get_worker(self, module_name: str, class_path: str) -> Type[Prototype]:
        """Loads a Python class from a given path and returns the instance.

        Args:
            module_name (str): Name of the module.
            class_path (str): Path to the Python class.

        Returns:
            Instance of Python class or None.
        """
        module_path, class_name = class_path.rsplit('.', 1)
        file_path = './' + module_path.replace('.', '/') + '.py'

        try:
            worker_class = getattr(import_module(module_path),
                                   class_name)
            worker = worker_class(module_name, class_path, self._manager)
        except AttributeError as e:
            self.logger.error(e)
            return

        return worker

    def has_module(self, name: str) -> bool:
        """Returns whether or not module is found.

        Args:
            name (str): The name of the module.

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
            class_path (str): The path to the class.

        Returns:
            True if module exists, False if not.
        """
        module_path, class_name = class_path.rsplit('.', 1)
        file_path = module_path.replace('.', '/') + '.py'

        if not Path(file_path).exists():
            return False

        return True

    def start(self, module_name: str) -> None:
        """Starts a module.

        Args:
            module_name (str): The name of the module.
        """
        self._modules.get(module_name).start()
        self._modules.get(module_name).start_worker()

    def stop(self, module_name: str) -> None:
        """Stops a module.

        Args:
            module_name (str): The name of the module.
        """
        self._modules.get(module_name).stop_worker()

    @property
    def modules(self) -> Dict:
        return self._modules


class SensorManager(object):
    """
    SensorManager stores and manages object of type `Sensor`.
    """

    def __init__(self, config_manager: Type[ConfigManager]):
        self.logger = logging.getLogger('sensorManager')
        self._sensor_config = config_manager.get('sensors')
        self._sensors = {}

        self.load()

    def load(self) -> None:
        """Creates the sensors defined in the configuration."""
        if not self._sensor_config:
            self.logger.info('No sensors defined')
            return

        for sensor_name, sensor_config in self._sensor_config.items():
            sensor_obj = Sensor(sensor_name, sensor_config)
            self.add(sensor_name, sensor_obj)
            self.logger.info('Created sensor "{}"'.format(sensor_name))

    def add(self, name: str, sensor: str) -> None:
        """Adds a sensor to the sensors dictionary."""
        self._sensors[name] = sensor

    def delete(self, name: str) -> None:
        """Removes a sensor from the sensors dictionary."""
        self._sensors[name] = None

    def get(self, name: str) -> Type[Sensor]:
        """Returns the sensor object with the given name."""
        return self._sensors.get(name)

    def get_sensors_names(self) -> List[str]:
        """Returns a list with all sensor names."""
        return self._sensors.keys()

    @property
    def sensors(self):
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
            data_type (str): The name of the data type (e.g., 'observation').
            path (str): The path to the JSON schema file.
            root (str): The root directory (default: 'schema').
        """
        schema_path = Path(root, path)

        if not schema_path.exists():
            self.logger.error('Schema file "{}" not found.'
                              .format(schema_path))
            return False

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
                return False
            except jsonschema.SchemaError:
                self.logger.error('Invalid JSON schema "{}"'
                                  .format(schema_path))
                return False

        return True

    def has_schema(self, name: str) -> bool:
        """Returns whether or not a JSON schema for the given name is
        available.

        Args:
            name (str): Name of the schema (e.g., 'observation').
        """
        if self._schema.get(name):
            return True
        else:
            return False

    def is_valid(self, data: Dict, schema_name: str) -> bool:
        """Validates data with JSON schema and returns result.

        Args:
            data (Dict): The data.
            schema_name (str): The name of the schema used for validation.

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
