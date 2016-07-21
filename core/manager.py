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
import queue
import threading
import time

from modules import port

logger = logging.getLogger('openadms')


class ConfigurationManager:

    def __init__(self):
        self._config = {}

    def load(self, file_name):
        """Loads configuration from JSON file."""
        if not os.path.exists(file_name):
            logger.error('Configuration file {} not found.'.format(file_name))
            # TODO: raise Exception
            return

        with open(file_name) as config_file:
            self._config = json.loads(config_file.read())
            logger.info('Loaded configuration file "{}"'.format(file_name))

    def dump(self):
        """Dumps the configuration to stdout."""
        encoded = json.dumps(self._config, sort_keys=True, indent=4)
        print(encoded)

    @property
    def config(self):
        return self._config

    @config.setter
    def config(self, config):
        self._config = config


class ModulesManager(object):

    """
    ModulesManager loads and manages Python modules.
    """

    def __init__(self, config_manager):
        self._workers = {}      # Workers for the modules.
        self._threads = {}      # Threads of the workers.

        self._config_manager = config_manager

    def add(self, module_name, class_path, output_queue):
        """Loads a class from a Python module and stores the instance in a
        dictionary."""
        module_path, class_name = class_path.rsplit('.', 1)
        file_path = module_path.replace('.', '/') + '.py'

        # TODO: Exception
        if not os.path.isfile(file_path):
            logger.error('Can\'t load module "{}": file "{}" not found'
                         .format(module_name, file_path))
            return

        class_inst = getattr(importlib.import_module(module_path),
                             class_name)(module_name, self._config_manager)

        # Create worker for the module.
        w = Worker(class_inst)

        # Run worker within a thread.
        t = threading.Thread(target=w.run, args=(output_queue, ))
        t.daemon = True
        t.start()

        # Add worker and thread.
        self._workers[module_name] = w
        self._threads[module_name] = t

        logger.debug('Loaded module "{}"'.format(module_name))

    def delete(self, module_name):
        """Deletes a module class instance."""
        self._threads[module_name] = None
        self._workers[module_name] = None

    @property
    def threads(self):
        return self._threads

    @property
    def workers(self):
        return self._workers


class SensorsManager(object):

    """
    SensorManager stores sensor.Sensor objects.
    """

    def __init__(self, config_manager):
        self._sensors = {}
        self._config_manager = config_manager

    def add(self, sensor_name, sensor):
        self._sensors[sensor_name] = sensor

    def delete(self, sensor_name):
        self._sensors[sensor_name] = None

    def get(self, name):
        return self._sensors[name]

    @property
    def sensors(self):
        return self._sensors


class Worker(object):

    """
    Worker binds a module to run the ``action()`` method within a thread.
    """

    def __init__(self, module, maxsize=10):
        self._module = module
        self._maxsize = maxsize
        self._input_queue = queue.Queue(self._maxsize)

    def put(self, obs_data):
        """Puts an observation data object into the queue."""
        if self._input_queue.full():
            logger.warning('Input queue of module "{}" is full '
                           '(> {} observations)'
                           .format(self._module.name, self._maxsize))
            return

        self._input_queue.put(obs_data)


    def run(self, output_queue):
        """Takes an observation data object from the input queue and puts the
        result of the callback function back into the output queue."""
        while True:
            if not self._input_queue.empty():
                obs_data = self._module.action(self._input_queue.get())

                if obs_data is None:
                    logger.warning('Module "{}" did not return any '
                                   'observation data'
                                   .format(self._module.name))
                    continue

                logger.debug('Sending observation "{}" to module "{}"'
                             .format(obs_data.get('Name'), self._module.name))

                # Flush the observation data.
                output_queue.put(obs_data)

            # Prevent thread from taking to much CPU time.
            time.sleep(0.01)

        self._module.destroy()

    @property
    def module(self):
        return self._module
