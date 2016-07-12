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

import logging
import queue
import threading
import time

from core import manager
from core import schedule
from core import sensor

"""Main monitoring module."""

logger = logging.getLogger('netadms')


class Monitor(threading.Thread):

    """
    Monitor is used to manage the monitoring process.
    """

    def __init__(self, config_file):
        threading.Thread.__init__(self)
        self.daemon = True              # Stop monitor thread on ^C.
        self._queue = queue.Queue()     # I/O queue for observation data.
        self._schedulers = {}           # One scheduler for every port.

        # Create the configuration manager and load the settings from the JSON
        # configuration file (e.g., './config/config.json').
        self._config_manager = manager.ConfigurationManager()
        self._config_manager.load(config_file)

        # Create the modules manager.
        self._modules_manager = manager.ModulesManager(self._config_manager)
        modules_config = self._config_manager.config['Modules']

        # Create the sensors manager.
        self._sensors_manager = manager.SensorsManager(self._config_manager)
        sensors_config = self._config_manager.config['Sensors']

        # Load modules using the modules manager.
        for module_name, class_path in modules_config.items():
            self._modules_manager.add(module_name, class_path, self._queue)

        # Create sensor objects.
        for sensor_name, sensor_config in sensors_config.items():
            logger.info('Created sensor {}'.format(sensor_name))
            sensor_inst = sensor.Sensor(sensor_name, self._config_manager)
            self._sensors_manager.add(sensor_name, sensor_inst)

        # List of assignments between sensors and serial ports
        # (sensor X on port Y).
        connections_config = self._config_manager.config['Connections']

        # Create observation data.
        for port_name, sensor_name in connections_config.items():
            try:
                schedules = self._config_manager.config['Scheduler'][port_name]
            except KeyError:
                logger.error('No scheduler found for port {}'.format(port_name))
                continue

            self._schedulers[port_name] = schedule.Scheduler()

            for s in schedules:
                job = schedule.Job(port_name,
                                   self._sensors_manager.get(sensor_name),
                                   s['Enabled'],
                                   s['StartDate'],
                                   s['EndDate'],
                                   s['Schedule'],
                                   s['ObservationSets'],
                                   self._queue)
                self._schedulers[port_name].add(job)

            self._schedulers[port_name].start()

    def run(self):
        """Takes observation data objects from the main queue and redirects
        them to the receiver modules."""
        while True:
            if not self._queue.empty():
                obs_data = self._queue.get()
                next_receiver = obs_data.get('Receivers').pop(0)

                if next_receiver not in self._modules_manager.workers:
                    logger.error('Module "{}" not found, discarding '
                                 'observation data'
                                 .format(next_receiver))
                    continue

                self._modules_manager.workers[next_receiver].put(obs_data)

            # Prevent thread from taking to much CPU time.
            time.sleep(0.01)

    @property
    def config_manager(self):
        return self._config_manager

    @property
    def modules_manager(self):
        return self._modules_manager

    @property
    def sensors_manager(self):
        return self._sensors_manager
