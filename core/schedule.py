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

import copy
import datetime as dt
import logging
import threading
import time

logger = logging.getLogger('netadms')


class Scheduler(threading.Thread):

    def __init__(self):
        threading.Thread.__init__(self)
        self.daemon = True
        self._jobs = []

    def add(self, job):
        self._jobs.append(job)
        logger.debug('Added new job to jobs list')

    def cancel(self, job):
        self._jobs.remove(job)

    def clear(self):
        del self._jobs[:]

    def run(self):
        while True:
            if len(self._jobs) > 0:
                for job in self._jobs:
                    if not job.enabled:
                        # logger.debug('Skipping disabled job')
                        continue

                    if job.has_expired():
                        self.cancel(job)
                        continue

                    if job.is_pending():
                        job.run()

            time.sleep(0.1)


class Job(object):

    def __init__(self, port_name, sensor, enabled, start_date, end_date,
        schedule, observation_sets, output_queue):
        self._port_name = port_name
        self._sensor = sensor
        self._enabled = enabled
        self._start_date = start_date
        self._end_date = end_date
        self._schedule = schedule
        self._observation_sets = observation_sets
        self._output_queue = output_queue

        self._date_fmt = '%Y-%m-%d'

    @property
    def enabled(self):
        return self._enabled

    def get_datetime(self, dt_str, dt_fmt):
        return dt.datetime.strptime(dt_str, dt_fmt)

    def has_expired(self):
        now = dt.datetime.now()
        end_dt = self.get_datetime(self._end_date, self._date_fmt)
        end_date = dt.datetime.combine(end_dt, dt.time.min)

        expired = False

        if now > end_date:
            expired = True
            logger.debug('Job has expired')

        return expired

    def is_pending(self):
        if not self._enabled:
            return False

        start_date = self.get_datetime(self._start_date, self._date_fmt)
        end_date = self.get_datetime(self._end_date, self._date_fmt)

        # Add a time ("00:00:00") to the day in order to make start and end
        # comparable.
        start_datetime = dt.datetime.combine(start_date, dt.time.min)
        end_datetime = dt.datetime.combine(end_date, dt.time.min)

        now = dt.datetime.now()

        # Are we within the date range of the job?
        if now >= start_datetime and now < end_datetime:
            if len(self._schedule) == 0:
                return True

            current_day = now.strftime('%A')    # Name of the current day.

            # Ignore current day if it is not in the schedule.
            if current_day in self._schedule:
                periods = self._schedule[current_day]

                # No given time range means the job should be executed
                # all day long.
                if len(periods) == 0:
                    return True

                # Check all time ranges of the current day.
                if len(periods) > 0:
                    time_fmt = '%H:%M:%S'

                    for p in periods:
                        # Start and end time of the current day.
                        start_time = self.get_datetime(p['StartTime'],
                                                       time_fmt).time()
                        end_time = self.get_datetime(p['EndTime'],
                                                     time_fmt).time()

                        # Are we within the time range of the current day?
                        if now.time() >= start_time and \
                            now.time() < end_time:
                            return True

        return False

    def run(self):
        for set_name in self._observation_sets:
            try:
                observation_set = self._sensor.get_observation_set(set_name)
            except KeyError:
                logger.error('Observation set "{}" not found'.format(set_name))
                continue

            logger.debug('Job is running observation set "{}" of sensor "{}" '
                         'on port "{}"'.format(set_name,
                                               self._sensor.name,
                                               self._port_name))

            for obs_data in observation_set:
                # Continue if observation is disabled.
                if not obs_data.get('Enabled'):
                    continue

                # Disable the observation if it should run one time only (for
                # instance, for initialization).
                if obs_data.get('Onetime'):
                    obs_data.set('Enabled', False)

                # Make a deep copy since we don't want to do any changes to the
                # observation data in our set.
                obs_data_copy = copy.deepcopy(obs_data)
                obs_data_copy.data['Receivers'].insert(0, self._port_name)

                sleep_time = obs_data_copy.get('SleepTime')

                # Put the observation data into the output queue (fire and
                # forget).
                self._output_queue.put(obs_data_copy)

                time.sleep(sleep_time)
