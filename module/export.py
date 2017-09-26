#!/usr/bin/env python3.6

"""Module for the export of observations."""

__author__ = 'Philipp Engel'
__copyright__ = 'Copyright (c) 2017 Hochschule Neubrandenburg'
__license__ = 'EUPL'

import arrow
import copy

from enum import Enum
from pathlib import Path

from core.manager import Manager
from core.observation import Observation
from module.prototype import Prototype


class FileRotation(Enum):
    """
    Enumeration of file rotation times of flat files.
    """

    NONE = 0
    DAILY = 1
    MONTHLY = 2
    YEARLY = 3


class FileExporter(Prototype):
    """
    FileExporter writes sensor data to a flat file in CSV format.

    Configuration:
        dateTimeFormat: Format of date and time (see Python strftime).
        fileExtension: The extension of the file (`.txt` or `.csv`).
        fileName: Placeholders are `{{date}}`, `{{target}}`, `{{name}}`,
            `{{port}}`.
        fileRotation: Either `none`, `daily`, `monthly`, or `yearly`.
        paths: Paths to save files to (multiple paths possible).
        separator: Separator between values within the CSV file.

    """

    def __init__(self, module_name: str, module_type: str, manager: Manager):
        super().__init__(module_name, module_type, manager)
        config = self.get_config(self._name)

        self._file_extension = config.get('fileExtension')
        self._file_name = config.get('fileName')
        self._file_rotation = {
            'none': FileRotation.NONE,
            'daily': FileRotation.DAILY,
            'monthly': FileRotation.MONTHLY,
            'yearly': FileRotation.YEARLY}.get(config.get('fileRotation'))
        self._date_time_format = config.get('dateTimeFormat')
        self._separator = config.get('separator')
        self._paths = config.get('paths')
        self._save_observation_id = config.get('saveObservationId')

    def process_observation(self, obs: Observation) -> Observation:
        """Append data to a flat file in CSV format.

        Args:
            obs: The input observation object.

        Returns:
            obs: The output observation object.
        """
        ts = arrow.get(obs.get('timeStamp', 0))

        file_date = {
            # No file rotation, i.e., all data is stored in a single file.
            FileRotation.NONE: None,
            # Every day a new file is created.
            FileRotation.DAILY: ts.format('YYYY-MM-DD'),
            # Every month a new file is created.
            FileRotation.MONTHLY: ts.format('YYYY-MM'),
            # Every year a new file is created.
            FileRotation.YEARLY: ts.format('YYYY')
        }[self._file_rotation]

        file_name = self._file_name
        file_name = file_name.replace('{{port}}', obs.get('portName'))
        file_name = file_name.replace('{{date}}', '{}'.format(file_date)
                                      if file_date else '')
        file_name = file_name.replace('{{target}}', '{}'
                                      .format(obs.get('target'))
                                      if obs.get('target') is not None else '')
        file_name = file_name.replace('{{name}}', '{}'.format(obs.get('name'))
                                      if obs.get('name') is not None else '')
        file_name += self._file_extension

        for path in self._paths:
            if not Path(path).exists():
                self.logger.error('Path "{}" does not exist'.format(path))
                continue

            file_path = Path(path, file_name)

            # Create a header if a new file has to be touched.
            header = None

            if not Path(file_path).is_file():
                header = '# Target "{}" of "{}" on "{}"\n' \
                         .format(obs.get('target'),
                                 obs.get('sensorName'),
                                 obs.get('portName'))

            # Open a file for every path.
            with open(str(file_path), 'a') as fh:
                # Add the header if necessary.
                if header:
                    fh.write(header)

                # Format the time stamp. For more information, see:
                # http://arrow.readthedocs.io/en/latest/#tokens
                date_time = ts.format(self._date_time_format)

                # Create the CSV line starting with date and time.
                line = date_time

                if self._save_observation_id:
                    line += self._separator + obs.get('id')

                if obs.get('target') is not None:
                    line += self._separator + obs.get('target')

                response_sets = obs.get('responseSets')

                for response_set_id in sorted(response_sets.keys()):
                    response_set = response_sets.get(response_set_id)

                    v = response_set.get('value')
                    u = response_set.get('unit')

                    line += self._separator + format(response_set_id)
                    line += self._separator + format(v)
                    line += self._separator + format(u)

                # Write line to file.
                fh.write(line + '\n')

                self.logger.info('Saved observation "{}" of target "{}" from '
                                 'port "{}" to file "{}"'
                                 .format(obs.get('name'),
                                         obs.get('target'),
                                         obs.get('portName'),
                                         str(file_path)))

        return obs


class RealTimePublisher(Prototype):
    """
    RealTimePublisher sends copies of `Observation` objects to a list of
    receivers.

    Configuration:
        receivers: List of modules to send the observation to.
        enabled: If or if not enabled.
    """

    def __init__(self, module_name: str, module_type: str, manager: Manager):
        super().__init__(module_name, module_type, manager)
        config = self.get_config(self._name)

        self._receivers = config.get('receivers')
        self._is_enabled = config.get('enabled')

    def process_observation(self, obs: Observation) -> Observation:
        if not self._is_enabled:
            return obs

        for receiver in self._receivers:
            obs_copy = copy.deepcopy(obs)

            target = receiver + '/' + obs_copy.get('target')

            obs_copy.set('nextReceiver', 0)
            obs_copy.set('receivers', [target])

            self.logger.debug('Publishing observation "{}" of target "{}" '
                              'to "{}"'.format(obs_copy.get('name'),
                                               obs_copy.get('target'),
                                               target))

            header = Observation.get_header()
            payload = obs_copy.data

            self.publish(target, header, payload)

        return obs
