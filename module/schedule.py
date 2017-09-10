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

"""Module for the scheduling of observations."""

__author__ = 'Philipp Engel'
__copyright__ = 'Copyright (c) 2017 Hochschule Neubrandenburg'
__license__ = 'EUPL'

import arrow
import copy
import logging
import threading
import time

from typing import *

from core.manager import Manager
from core.observation import Observation
from module.prototype import Prototype


class Job(object):
    """
    Job stores an observation object and sends it to a callback function if the
    current date and time are within the set schedule.
    """

    def __init__(self,
                 name: str,
                 port_name: str,
                 obs: Observation,
                 is_enabled: bool,
                 start_date: str,
                 end_date: str,
                 weekdays: Dict[str, List],
                 uplink: Callable[[str, Dict[str, Any], Dict[str, Any]], None]):
        self._name = name               # Name of the job.
        self._port_name = port_name     # Name of the port.
        self._obs = obs                 # Observation object.
        self._is_enabled = is_enabled   # Is enabled or not.
        self._weekdays = weekdays       # The time sheet.
        self._uplink = uplink           # Callback function.

        self.logger = logging.getLogger('job')

        # Used date and time formats.
        self._date_fmt = 'YYYY-MM-DD'
        self._time_fmt = 'HH:mm:ss'

        self._start_date = arrow.get(start_date, self._date_fmt)
        self._end_date = arrow.get(end_date, self._date_fmt)

    def has_expired(self) -> bool:
        """Checks if the job has expired."""
        now = arrow.now()

        if now > self._end_date:
            self.logger.debug('Job "{}" has expired'.format(self._name))
            return True

        return False

    def is_pending(self) -> bool:
        """Checks whether or not the job is within the current time frame and
        ready for processing."""
        if not self._is_enabled:
            return False

        now = arrow.now()

        # Are we within the date range of the job?
        if self._start_date <= now < self._end_date:
            # No days defined, go on.
            if len(self._weekdays) == 0:
                return True

            # Name of the current day (e.g., "monday").
            current_day = arrow.now().format('dddd').lower()

            # Ignore current day if it is not listed in the schedule.
            if current_day in self._weekdays:
                # Time ranges of the current day.
                periods = self._weekdays.get(current_day)

                # No given time range means the job should be executed
                # all day long.
                if len(periods) == 0:
                    return True

                # Check all time ranges of the current day.
                if len(periods) > 0:
                    for period in periods:
                        # Start and end time of the current day.
                        start_time = arrow.get(period.get('startTime'),
                                               self._time_fmt).time()
                        end_time = arrow.get(period.get('endTime'),
                                             self._time_fmt).time()

                        # Are we within the time range of the current day?
                        if start_time <= now.time() < end_time:
                            return True

        return False

    def run(self) -> None:
        """Iterates trough the observation set and sends observations to an
        external callback function."""
        # Return if observation is disabled.
        if not self._obs.get('enabled'):
            return

        # Disable the observation if it should run one time only.
        if self._obs.get('onetime'):
            self._obs.set('enabled', False)

        # Make a deep copy, since we don't want to do any changes to the
        # observation in our observation set.
        obs_copy = copy.deepcopy(self._obs)

        # Generate a new UUID4.
        obs_copy.set('id', Observation.get_new_id())

        # Insert the name of the port module or the virtual sensor at the
        # beginning of the receivers list.
        receivers = obs_copy.get('receivers')
        receivers.insert(0, self._port_name)
        obs_copy.set('receivers', receivers)

        # Set the next receiver to the module following the port.
        obs_copy.set('nextReceiver', 1)

        self.logger.debug('Starting job "{}" for port "{}"'
                          .format(self._obs.get('name'),
                                  self._port_name))

        # Get the sleep time of the whole observation.
        sleep_time = obs_copy.get('sleepTime', 0)

        # Create target, header, and payload in order to send the observation.
        target = self._port_name
        header = Observation.get_header()
        payload = obs_copy.data

        # Fire and forget the observation.
        self._uplink(target, header, payload)

        # Sleep until the next observation.
        self.logger.debug('Next observation in {} s'.format(sleep_time))
        time.sleep(sleep_time)

    @property
    def is_enabled(self):
        return self._is_enabled

    @property
    def name(self):
        return self._name


class Scheduler(Prototype):
    """
    Scheduler is used to manage the monitoring process by sending observations
    to a sensor. Each observation is represented by a single job. Jobs are
    stored in a jobs list and will be executed at the given date and time. A
    separate scheduler is necessary for each serial port.

    Configuration:
        port: Name of the port module.
        sensor: Name of the sensor.
        schedules: List of schedules.
    """

    def __init__(self, module_name: str, module_type: str, manager: Manager):
        super().__init__(module_name, module_type, manager)
        self._config = self.get_config('schedulers', self._name)

        self._port_name = self._config.get('port')
        self._sensor_name = self._config.get('sensor')
        self._schedules = self._config.get('schedules')

        self._thread = None
        self._jobs = []

    def add(self, job: Job) -> None:
        """Appends a job to the jobs list."""
        self._jobs.append(job)
        self.logger.debug('Added job "{}" to scheduler "{}"'
                          .format(job.name, self._name))

    def load_jobs(self) -> None:
        """Loads all observation sets from the configurations and creates jobs
        to put into the jobs list."""
        # Run through the schedules and create jobs.
        for schedule in self._schedules:
            observations = schedule.get('observations')

            # Get all observations of the current observation set.
            for obs_name in observations:
                obs = self._sensor_manager.get(self._sensor_name)\
                                          .get_observation(obs_name)

                if not obs:
                    self.logger.error('Observation "{}" not found'
                                      .format(obs_name))
                    continue

                # Add sensor name to the observation.
                obs.set('sensorName', self._sensor_name)

                # Create a new job.
                job = Job(obs_name,
                          self._port_name,
                          obs,
                          schedule.get('enabled'),
                          schedule.get('startDate'),
                          schedule.get('endDate'),
                          schedule.get('weekdays'),
                          self.publish)
                # Add the job to the jobs list.
                self.add(job)

    def run(self) -> None:
        """Threaded method to process the jobs queue."""
        self.load_jobs()
        zombies = []

        # FIXME: Wait for uplink connection.
        sleep_time = 5.0
        self.logger.info('Starting jobs in {:3.1f} s'.format(sleep_time))
        time.sleep(sleep_time)

        while self.is_running:
            t1 = time.time()

            if not self._is_running:
                break

            for job in self._jobs:
                if job.has_expired():
                    zombies.append(job)
                    continue

                if not job.is_enabled:
                    continue

                if job.is_pending():
                    job.run()

            # Remove expired jobs from the jobs list.
            while zombies:
                zombie = zombies.pop()
                self.logger.debug('Deleting expired job "{}"'
                                  .format(zombie.name))
                self._jobs.remove(zombie)

            t2 = time.time()
            dt = t2 - t1

            if dt < 0.1:
                time.sleep(0.1 - dt)

    def start(self) -> None:
        if self._is_running:
            return

        # self.logger.debug('Starting worker "{}"'
        #                   .format(self._name))
        self._is_running = True

        # Run the method run() within a thread.
        self._thread = threading.Thread(target=self.run)
        self._thread.daemon = True
        self._thread.start()
