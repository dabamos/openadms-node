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

import importlib
import json
import logging
import os

from typing import *

from core.intercom import MQTTMessenger
from core.module import Module
from core.sensor import Sensor


class Managers(object):

    def __init__(self):
        self._config_manager = None
        self._sensor_manager = None
        self._module_manager = None

    @property
    def config_manager(self):
        return self._config_manager

    @property
    def module_manager(self):
        return self._module_manager

    @property
    def sensor_manager(self):
        return self._sensor_manager

    @config_manager.setter
    def config_manager(self, config_manager):
        self._config_manager = config_manager

    @module_manager.setter
    def module_manager(self, module_manager):
        self._module_manager = module_manager

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
        self._path = path   # Path of the configuration file.

        if self._path:
            self.load(self._path)
        else:
            self.logger.error('No configuration file set')

    def load(self, config_path: str) -> bool:
        """Loads configuration from JSON file."""
        if not os.path.exists(config_path):
            self.logger.error('Configuration file "{}" not found.'
                              .format(config_path))
            return False

        with open(config_path) as config_file:
            try:
                self._config = json.loads(config_file.read())
                self.logger.info('Loaded configuration file "{}"'
                                 .format(config_path))
            except ValueError as e:
                self.logger.error('Invalid JSON: "{}"'.format(e))
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
        """Path to the configuration file.
        
        Returns:
            String with path.
        """
        return self._path

    @config.setter
    def config(self, config: Dict) -> None:
        self._config = config


class ModuleManager(object):
    """
    ModuleManager loads and manages OpenADMS modules.
    """

    def __init__(self, managers):
        self.logger = logging.getLogger('moduleManager')
        self._managers = managers
        self._config = self._managers.config_manager.get('modules')
        self._modules = {}

        for module_name, class_path in self._config.items():
            self.add(module_name, class_path)

    def add(self, module_name, class_path):
        """Instantiates a worker, instantiates a messenger, and bundles both
        to a module. The module will be added to the modules dictionary."""
        worker = self.get_worker(module_name, class_path)
        messenger = MQTTMessenger(self._managers.config_manager)
        module = Module(messenger, worker)
        module.start()

        # Add the module to the modules dictionary.
        self._modules[module_name] = module
        # Start the threaded module.
        self.logger.debug('Starting module "{}" ...'.format(module_name))

    def delete(self, module_name):
        """Removes a module from the modules dictionary."""
        self._modules[module_name] = None

    def get_worker(self, module_name, class_path):
        """Loads a Python class from a given path and returns the instance."""
        module_path, class_name = class_path.rsplit('.', 1)
        file_path = module_path.replace('.', '/') + '.py'

        if not os.path.isfile(file_path):
            self.logger.error('File "{}" not found'.format(file_path))
            return

        try:
            worker_class = getattr(importlib.import_module(module_path),
                                   class_name)
            worker = worker_class(module_name, class_path, self._managers)
        except AttributeError as e:
            self.logger.error(e)
            return

        return worker

    def start(self, module_name: str) -> None:
        self._modules.get(module_name).start()

    def stop(self, module_name: str) -> None:
        self._modules.get(module_name).stop()

    @property
    def modules(self):
        return self._modules


class SensorManager(object):
    """
    SensorManager stores and manages object of type `Sensor`.
    """

    def __init__(self, config_manager):
        self.logger = logging.getLogger('sensorManager')
        self._sensor_config = config_manager.get('sensors')
        self._sensors = {}

        self.load()

    def load(self):
        """Creates the sensors defined in the configuration."""
        # Create sensor objects.
        for sensor_name, sensor_config in self._sensor_config.items():
            sensor_obj = Sensor(sensor_name, sensor_config)
            self.add(sensor_name, sensor_obj)
            self.logger.info('Created sensor {}'.format(sensor_name))

    def add(self, name, sensor):
        """Adds a sensor to the sensors dictionary."""
        self._sensors[name] = sensor

    def delete(self, name):
        """Removes a sensor from the sensors dictionary."""
        self._sensors[name] = None

    def get(self, name):
        """Returns the sensor object with the given name."""
        return self._sensors.get(name)

    def get_sensors_names(self):
        return self._sensors.keys()

    @property
    def sensors(self):
        return self._sensors
