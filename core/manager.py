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

import importlib
import json
import logging
import os

from core.intercom import MQTTMessenger
from core.sensor import Sensor
from modules.prototype import *

"""Collection of manager classes."""

logger = logging.getLogger('openadms')


class ConfigurationManager:

    """
    ConfigurationManager loads and stores the configuration.
    """

    def __init__(self, config_file):
        self._config = {}

        if config_file:
            try:
                self.load(config_file)
            except json.decoder.JSONDecodeError as e:
                logger.error('Invalid JSON: "{}"'.format(e))
        else:
            logger.warning('No configuration file set')

    def load(self, file_name):
        """Loads configuration from JSON file."""
        if not os.path.exists(file_name):
            logger.error('Configuration file "{}" not found.'.format(file_name))
            return

        with open(file_name) as config_file:
            self._config = json.loads(config_file.read())
            logger.info('Loaded configuration file "{}"'.format(file_name))

    def dump(self):
        """Dumps the configuration to stdout."""
        encoded = json.dumps(self._config, sort_keys=True, indent=4)
        print(encoded)

    def get(self, key):
        return self._config.get(key)

    @property
    def config(self):
        return self._config

    @config.setter
    def config(self, config):
        self._config = config


class ModuleManager(object):

    """
    ModuleManager loads and manages OpenADMS modules.
    """

    def __init__(self, config_manager, sensor_manager):
        self._config_manager = config_manager
        self._sensor_manager = sensor_manager

        config = self._config_manager.get('Modules')
        self._modules = {}

        for module_name, class_path in config.items():
            self.add(module_name, class_path)

    def add(self, module_name, class_path):
        """Instantiates a worker, instantiates a messenger, and bundles both
        into a module. The module will be added to the modules dictionary."""
        worker = self._get_worker(module_name, class_path)
        messenger = MQTTMessenger(self._config_manager)
        module = Module(messenger, worker)

        # Add the module to the modules dictionary.
        # Start the module (as it is a thread).
        self._modules[module_name] = module
        module.start()

        # Module has been started.
        logger.debug('Started module "{}"'.format(module_name))

    def _get_worker(self, module_name, class_path):
        """Load a Python class from a given path and return the instance."""
        module_path, class_name = class_path.rsplit('.', 1)
        file_path = module_path.replace('.', '/') + '.py'

        if not os.path.isfile(file_path):
            logger.error('File "{}" not found'.format(file_path))
            return

        try:
            worker = getattr(importlib.import_module(module_path),
                             class_name)(module_name,
                                         self._config_manager,
                                         self._sensor_manager)
        except AttributeError:
            logger.error('Module "{}" not found'.format(class_path))
            return

        return worker

    def delete(self, module_name):
        """Removes a module from the modules dictionary."""
        self._modules[module_name] = None

    @property
    def modules(self):
        return self._modules


class SensorManager(object):

    """
    SensorManager stores Sensor objects.
    """

    def __init__(self, config_manager):
        self._sensors = {}
        self._config_manager = config_manager
        self.load()

    def load(self):
        """Creates the sensors defined in the configuration."""
        sensors = self._config_manager.get('Sensors')

        # Create sensor objects.
        for sensor_name, sensor_config in sensors.items():
            sensor_obj = Sensor(sensor_name, self._config_manager)
            self.add(sensor_name, sensor_obj)
            logger.info('Created sensor {}'.format(sensor_name))

    def add(self, name, sensor):
        """Adds a sensor to the sensors dictionary."""
        self._sensors[name] = sensor

    def delete(self, name):
        """Removes a sensor from the sensors dictionary."""
        self._sensors[name] = None

    def get(self, name):
        """Returns the sensor object with the given name."""
        return self._sensors.get(name)

    @property
    def sensors(self):
        return self._sensors
