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

logger = logging.getLogger('openadms')


class Monitor(threading.Thread):

    """
    Monitor is used to manage the monitoring process.
    """

    def __init__(self, config_file):
        threading.Thread.__init__(self)
        self.daemon = True              # Stop monitor thread on ^C.
        self._queue = queue.Queue()     # I/O queue for observation data.
        self._schedulers = {}           # Scheduler objects go in here.

        # Create the configuration manager and load the settings from the JSON
        # configuration file (e.g., './config/config.json').
        self._config_manager = manager.ConfigurationManager()
        self._config_manager.load(config_file)

        # Create the modules manager.
        self._module_manager = manager.ModuleManager(self._config_manager)
        module_config = self._config_manager.config['Modules']

        # Create the sensors manager.
        self._sensor_manager = manager.SensorManager(self._config_manager)
        sensor_config = self._config_manager.config['Sensors']

        # Load modules using the modules manager.
        for module_name, class_path in module_config.items():
            self._module_manager.add(module_name, class_path, self._queue)

        # Create sensor objects.
        for sensor_name, sensor_config in sensor_config.items():
            logger.info('Created sensor {}'.format(sensor_name))
            sensor_inst = sensor.Sensor(sensor_name, self._config_manager)
            self._sensor_manager.add(sensor_name, sensor_inst)

        self._init_schedulers()

    def _init_schedulers(self):
        """Initializes all the schedulers."""
        logger.debug('Initializing schedulers ...')

        # List of assignments between sensors and serial ports
        # (sensor X on port Y).
        connections_config = self._config_manager.config['Connections']

        # Create schedulers.
        for port_name, sensor_name in connections_config.items():
            try:
                port_schedules = self._config_manager.config['Scheduler'][port_name]
            except KeyError:
                logger.error('No schedule found for port {}'.format(port_name))
                continue

            # Create a new scheduler for every port (e.g., "USB0", ...).
            self._schedulers[port_name] = schedule.Scheduler(self._queue)

            # Run through the port schedules and create jobs.
            for port_schedule in port_schedules:
                job_names = port_schedule['ObservationSets']

                for job_name in job_names:
                    # Create new job.
                    job = schedule.Job(job_name,
                                       port_name,
                                       self._sensor_manager.get(sensor_name),
                                       port_schedule['Enabled'],
                                       port_schedule['StartDate'],
                                       port_schedule['EndDate'],
                                       port_schedule['Schedule'])
                    # Add job to the scheduler.
                    self._schedulers[port_name].add(job)

            # Start the scheduler thread.
            self._schedulers[port_name].start()

    def run(self, sleep_time = 0.01):
        """Takes observation data objects from the main queue and redirects
        them to the receiver modules."""
        while True:
            if self._queue.empty():
                # Prevent thread from taking to much CPU time.
                time.sleep(sleep_time)
                continue

            obs = self._queue.get()

            # No receivers definied.
            if len(obs.get('Receivers')) == 0:
                logging.debug('No receivers defined for observation "{}"'
                              .format(obs.get('Name')))
                continue

            # Index of the receivers list.
            index = obs.get('NextReceiver')

            # No index definied.
            if (index is None) or (index < 0):
                logger.warning('Next receiver of observation "{}" not '
                               'defined'.format(obs.get('Name')))
                continue

            # Receivers list has been processed.
            if index >= len(obs.get('Receivers')):
                logger.info('Observation "{}" has been finished'
                            .format(obs.get('Name')))
                continue

            # Get the name of the next receiver.
            next_receiver = obs.get('Receivers')[index]

            # Set the index to the subsequent receiver.
            index = index + 1
            obs.set('NextReceiver', index)

            if next_receiver not in self._module_manager.workers:
                logger.error('Module "{}" not found, discarding '
                             'observation "{}"'
                             .format(next_receiver, obs.get('Name')))
                continue

            # Fire and forget.
            self._module_manager.workers[next_receiver].put(obs)

    @property
    def config_manager(self):
        return self._config_manager

    @property
    def module_manager(self):
        return self._module_manager

    @property
    def sensor_manager(self):
        return self._sensor_manager
