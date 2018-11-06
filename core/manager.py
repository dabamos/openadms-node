#!/usr/bin/env python3.6

"""Collection of manager classes."""

__author__ = 'Philipp Engel'
__copyright__ = 'Copyright (c) 2018 Hochschule Neubrandenburg'
__license__ = 'BSD-2-Clause'

import json
import logging
import re

from importlib import import_module
from pathlib import Path
from typing import Any, Dict, KeysView

import arrow
import jsonschema

from core.intercom import MQTTMessenger
from core.module import Module
from core.sensor import Sensor
from core.prototype import Prototype


class Manager:
    """
    Manager is a container class for all the managers.
    """

    def __init__(self):
        self._config = None
        self._module = None
        self._node = None
        self._project = None
        self._schema = None
        self._sensor = None

    @property
    def config(self) -> Any:
        return self._config

    @property
    def module(self) -> Any:
        return self._module

    @property
    def node(self) -> Any:
        return self._node

    @property
    def project(self) -> Any:
        return self._project

    @property
    def schema(self) -> Any:
        return self._schema

    @property
    def sensor(self) -> Any:
        return self._sensor

    @config.setter
    def config(self, config_manager):
        self._config = config_manager

    @module.setter
    def module(self, module_manager):
        self._module = module_manager

    @node.setter
    def node(self, node_manager):
        self._node = node_manager

    @project.setter
    def project(self, project_manager):
        self._project = project_manager

    @schema.setter
    def schema(self, schema_manager):
        self._schema = schema_manager

    @sensor.setter
    def sensor(self, sensor_manager):
        self._sensor = sensor_manager


class ConfigManager:
    """
    ConfigManager loads and stores the OpenADMS Node configuration.
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

        self.load_all()

    def load_all(self):
        """Loads the configuration."""
        self._config = {}

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
            self.logger.error(f'Configuration file "{config_path}" not found.')
            return False

        with open(config_path) as config_file:
            try:
                self._config = json.loads(config_file.read())
                self.logger.info(f'Loaded configuration file "{config_path}"')
            except ValueError as e:
                self.logger.error(f'Invalid JSON file "{e}"')
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
                         *args) -> Dict[str, Any]:
        """
        Returns the validated configuration of a module. Raises a ValueError
        exception if the configuration is invalid.

        Args:
            schema_name: Name of the JSON schema.
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

        # Check whether module's configuration is valid.
        if not self._schema_manager.is_valid(config, schema_name):
            raise ValueError(f'Configuration of "{schema_name}" is invalid')

        return config

    def remove_all(self) -> None:
        """Clears everything."""
        self._config = {}

    @property
    def config(self) -> Dict[str, Any]:
        return self._config

    @property
    def path(self) -> str:
        return self._path

    @config.setter
    def config(self, config: Dict[str, Any]) -> None:
        self._config = config


class ModuleManager:
    """
    ModuleManager loads and manages OpenADMS Node modules.
    """

    def __init__(self, manager: Manager):
        """
        Args:
            manager: The manager object.
        """
        self.logger = logging.getLogger('moduleManager')
        self._manager = manager
        # Quirky work-around:
        self._manager.module = self

        self._start_time = None
        self._modules = {}

        self.load_all()

    def add(self, name: str, class_path: str):
        """Instantiates a worker, instantiates a messenger, and bundles both
        to a module. The module will be added to the modules dictionary.

        Args:
            name: The name of the module.
            class_path: The path to the Python class.

        Returns:
            True if module has been added, False if not.

        Raises:
            ValueError: If module file not exists.
        """
        if not self.module_exists(class_path):
            raise ValueError(f'Module "{class_path}" not found')

        messenger = MQTTMessenger(self._manager, name)
        worker = self.get_worker_instance(name, class_path)

        self._modules[name] = Module(messenger, worker)
        self.logger.debug(f'Loaded module "{name}"')

    def get(self, name: str) -> Module:
        """Returns a specific module.

        Args:
            name: The name of the module.
        """
        return self._modules.get(name)

    def get_modules_list(self) -> KeysView:
        """Returns a list with all names of all modules.

        Returns:
            List of modules names.
        """
        return self._modules.keys()

    def get_worker_instance(self, module_name: str,
                            class_path: str) -> Prototype:
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
        return True if self._modules.get(name) else False

    def kill(self, name: str) -> None:
        """Kills a module (stops worker and messenger).

        Args:
            name: The name of the module.
        """
        if self.has_module(name):
            self._modules.get(name).stop_worker()
            self._modules.get(name).stop()

    def kill_all(self) -> None:
        """Kills all modules (stops all workers and messengers)."""
        for module_name in self._modules:
            self.kill(module_name)

    def load_all(self) -> None:
        """Loads all modules."""
        self._modules = {}
        self._manager.schema.add_schema('modules', 'core/modules.json')
        config = self._manager.config.get_valid_config('modules',
                                                       'core',
                                                       'modules')

        if not config:
            self.logger.warning('No modules defined')

        for module_name, class_path in config.items():
            try:
                self.add(module_name, class_path)
            except Exception as e:
                self.logger.error(f'Loading module "{module_name}" failed: '
                                  f'{str(e)}')
                continue

        # Start-time of the monitoring software.
        self._start_time = arrow.now()

    def module_exists(self, class_path: str) -> bool:
        """Returns whether or not a OpenADMS Node module exists at the given
        class path.

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

    def remove(self, name: str) -> None:
        """Removes a module.

        Args:
            name: The name of the module.
        """
        if self.has_module(name):
            self.logger.info(f'Removing module "{name}" ...')
            self._modules[name].stop_worker()
            self._modules[name].stop()
            self._modules[name] = None

    def remove_all(self) -> None:
        """Removes all modules."""
        for module_name in self._modules:
            self.remove(module_name)

        self._modules = {}

    def start(self, name: str) -> None:
        """Starts a module.

        Args:
            name: The name of the module.
        """
        self.logger.debug(f'Starting module "{name}" ...')
        self._modules.get(name).start()
        self._modules.get(name).start_worker()

    def start_all(self) -> None:
        """Starts all modules."""
        for name in self._modules:
            self.start(name)

    def stop(self, name: str) -> None:
        """Stops a module.

        Args:
            name: The name of the module.
        """
        self._modules.get(name).stop_worker()

    def stop_all(self) -> None:
        """Stops all modules."""
        for module_name in self._modules:
            self.stop(module_name)

    @property
    def modules(self) -> Dict[str, Module]:
        return self._modules


class Node:
    """
    Node stores name, description, and ID of the sensor node.
    """

    def __init__(self, name: str, id: str, description: str):
        self._name = name
        self._description = description
        self._id = re.sub('[^a-zA-Z0-9_-]', '', id)

    @property
    def description(self) -> str:
        return self._description

    @property
    def id(self) -> str:
        return self._id

    @property
    def name(self) -> str:
        return self._name

    @description.setter
    def description(self, description: str) -> None:
        self._description = description

    @id.setter
    def id(self, id: str) -> None:
        # Remove non-word characters from node id.
        self._id = re.sub('[^a-zA-Z0-9_-]', '', id)

    @name.setter
    def name(self, name: str) -> None:
        self._name = name


class NodeManager:
    """
    NodeManager loads and stores the node configuration.
    """

    def __init__(self, manager: Manager):
        """
        Args:
            manager: The manager object.
        """
        self.logger = logging.getLogger('nodeManager')
        self._manager = manager
        self._node = None

        self.load_all()

    def load_all(self) -> None:
        """Loads node configuration."""
        self._node = None

        # Configuration of the node.
        self._manager.schema.add_schema('node', 'core/node.json')
        config = self._manager.config.get_valid_config('node', 'core', 'node')

        # Node information.
        self._node = Node(config.get('name'),
                          config.get('id'),
                          config.get('description'))

    def remove_all(self) -> None:
        """Clears everything."""
        self.logger.info(f'Removing node "{self._node.name}" ...')
        self._node = None

    @property
    def node(self) -> Node:
        return self._node


class Project:
    """
    Project stores name, description, and ID of the monitoring project.
    """

    def __init__(self, name: str, id: str, description: str):
        self._name = name
        self._description = description
        self._id = re.sub('[^a-zA-Z0-9_-]', '', id)

    @property
    def description(self) -> str:
        return self._description

    @property
    def id(self) -> str:
        return self._id

    @property
    def name(self) -> str:
        return self._name

    @description.setter
    def description(self, description: str) -> None:
        self._description = description

    @id.setter
    def id(self, id: str) -> None:
        # Remove non-word characters from project id.
        self._id = re.sub('[^a-zA-Z0-9_-]', '', id)

    @name.setter
    def name(self, name: str) -> None:
        self._name = name


class ProjectManager:
    """
    ProjectManager loads and stores the project configuration.
    """

    def __init__(self, manager: Manager):
        """
        Args:
            manager: The manager object.
        """
        self.logger = logging.getLogger('projectManager')
        self._manager = manager
        self._project = None
        self.load_all()

    def load_all(self) -> None:
        """Loads the project configuration and meta information."""
        self._project = None
        self._manager.schema.add_schema('project', 'core/project.json')
        config = self._manager.config.get_valid_config('project',
                                                       'core',
                                                       'project')
        # Project meta information.
        self._project = Project(config.get('name'),
                                config.get('id'),
                                config.get('description'))

    def remove_all(self) -> None:
        """Clears everything."""
        self.logger.info(f'Removing project "{self._project.name}" ...')
        self._project = None

    @property
    def project(self) -> Project:
        return self._project


class SchemaManager:
    """
    SchemaManager stores JSON schemas and validates given data with them.
    """

    def __init__(self, schemas_root_path: str = 'schemas'):
        self.logger = logging.getLogger('schemaManager')
        self._schemas = {}
        self._schemas_root_path = schemas_root_path
        self.load_all()

    def add_schema(self,
                   data_type: str,
                   path: str) -> bool:
        """Reads a JSON schema file from the given path and stores it in the
        internal dictionary.

        Args:
            data_type: The name of the data type (e.g., 'observation').
            path: The path to the JSON schema file.

        Returns:
            True if schema has been added, False if not.
        """
        if self._schemas.get(data_type):
            return False

        schema_path = Path(self._schemas_root_path, path)

        if not schema_path.exists():
            self.logger.error(f'Schema file "{schema_path}" not found.')
            return False

        with open(str(schema_path), encoding='utf-8') as data_file:
            try:
                schema = json.loads(data_file.read())
                jsonschema.Draft4Validator.check_schema(schema)

                self._schemas[data_type] = schema
                self.logger.debug(f'Loaded schema "{data_type}"')
            except json.JSONDecodeError:
                self.logger.error(f'Invalid JSON file "{schema_path}"')
                return False
            except jsonschema.SchemaError:
                self.logger.error(f'Invalid JSON schema "{schema_path}"')
                return False

        return True

    def get_schema_path(self, class_path: str) -> Path:
        """Uses the class path of a module to generate the path to the
        configuration schema file.

        For instance, the given class path `modules.schedule.Scheduler` will be
        converted to the file path `modules/schedule/scheduler.json`.

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
        if self._schemas.get(name):
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
            self.logger.warning(f'JSON schema "{schema_name}" not found')
            return False

        try:
            schema = self._schemas.get(schema_name)
            jsonschema.validate(data, schema)
        except jsonschema.ValidationError:
            return False

        return True

    def load_all(self) -> None:
        """Initialises the schemas dictionary."""
        self._schemas = {}
        self.add_schema('observation', 'observation.json')

    def remove(self, name: str) -> None:
        """Removes a schema.

        Args:
            name: The name of the schema.
        """
        self.logger.info(f'Removing schema "{name}" ...')
        self._schemas[name] = None

    def remove_all(self) -> None:
        """Removes all schemas."""
        for schema_name in self._schemas:
            self.remove(schema_name)

        self._schemas = {}


class SensorManager:
    """
    SensorManager stores and manages objects of type `Sensor`.
    """

    def __init__(self, config_manager: ConfigManager):
        """
        Args:
            config_manager: The configuration manager.
        """
        self.logger = logging.getLogger('sensorManager')
        self._sensors_config = config_manager.get('sensors')
        self._sensors = {}

        self.load_all()

    def load_all(self) -> None:
        """Creates the sensors defined in the configuration."""
        self._sensors = {}

        if not self._sensors_config:
            self.logger.warning('No sensors defined')
            return

        for sensor_name, sensor_config in self._sensors_config.items():
            sensor_obj = Sensor(sensor_name, sensor_config)
            self.add_sensor(sensor_name, sensor_obj)
            self.logger.info(f'Loaded sensor "{sensor_name}"')

    def add_sensor(self, name: str, sensor: Sensor) -> None:
        """Adds a sensor to the sensors dictionary.

        Args:
            name: The name of the sensor.
            sensor: The sensor object.
        """
        self._sensors[name] = sensor

    def remove(self, name: str) -> None:
        """Removes a sensor from the sensors dictionary."""
        self.logger.info(f'Removing sensor "{name}" ...')
        self._sensors[name] = None

    def remove_all(self) -> None:
        """Removes all sensors."""
        for sensor_name in self._sensors:
            self.remove(sensor_name)

        self._sensors = {}

    def get(self, name: str) -> Sensor:
        """Returns the sensor object with the given name."""
        return self._sensors.get(name)

    def get_sensors_names(self) -> KeysView:
        """Returns a list with all sensor names."""
        return self._sensors.keys()

    @property
    def sensors(self) -> Dict[str, Sensor]:
        return self._sensors

