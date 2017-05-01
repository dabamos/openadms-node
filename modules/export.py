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

__author__ = 'Philipp Engel'
__copyright__ = 'Copyright (c) 2017 Hochschule Neubrandenburg'
__license__ = 'EUPL'

import copy
import os

from datetime import datetime
from enum import Enum

from modules.prototype import Prototype

"""Module for the export of sensor data to files and databases."""


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
    """

    def __init__(self, name, type, manager):
        Prototype.__init__(self, name, type, manager)
        config = self._config_manager.get(self._name)

        self._file_extension = config.get('fileExtension')
        self._file_name = config.get('fileName')
        self._file_rotation = {
            'none': FileRotation.NONE,
            'daily': FileRotation.DAILY,
            'monthly': FileRotation.MONTHLY,
            'yearly': FileRotation.YEARLY}.get(config.get('fileRotation'))
        self._date_time_format = config.get('dateTimeFormat')
        self._separator = config.get('separator')
        self._paths = self._revise_paths(config.get('paths'))

    def _revise_paths(self, paths):
        """Checks whether the paths in a given list end with ``\``. Adds the
        character if it is missing.

        Args:
            paths (List[str]): The list of paths to check.

        Returns:
            List[str]: The revised list of paths.
        """
        for i, p in enumerate(paths):
            if p != '' and not p.endswith('/'):
                paths[i] += '/'

        return paths

    def process_observation(self, obs):
        """Append data to a flat file in CSV format.

        Args:
            obs (Observation): The input observation object.

        Returns:
            obs (Observation): The output observation object.
        """
        ts = datetime.fromtimestamp(obs.get('timeStamp', 0))

        date = {
            # No file rotation, i.e., all data is stored in a single file.
            FileRotation.NONE: None,
            # Every day a new file is created.
            FileRotation.DAILY: ts.strftime('%Y-%m-%d'),
            # Every month a new file is created.
            FileRotation.MONTHLY: ts.strftime('%Y-%m'),
            # Every year a new file is created.
            FileRotation.YEARLY: ts.strftime('%Y')
        }[self._file_rotation]

        file_name = self._file_name

        file_name = file_name.replace('{port}', obs.get('portName'))
        file_name = file_name.replace('{date}', '{}'.format(date)
                                      if date else '')
        file_name = file_name.replace('{id}', '{}'.format(obs.get('id'))
                                      if obs.get('id') is not None else '')
        file_name = file_name.replace('{name}', '{}'.format(obs.get('name'))
                                      if obs.get('name') is not None else '')

        file_name += self._file_extension

        for path in self._paths:
            if not os.path.isdir(path):
                self.logger.error('Path "{}" does not exist'.format(path))
                continue

            # Create a header if a new file has to be touched.
            header = None

            if not os.path.isfile(path + file_name):
                header = '# Target "{}" of "{}" on "{}"\n' \
                         .format(obs.get('id'),
                                 obs.get('sensorName'),
                                 obs.get('portName'))
            # Open a file for every path.
            with open(path + file_name, 'a') as fh:
                # Add the header if necessary.
                if header:
                    fh.write(header)

                # Convert Unix time stamp to date and time.
                dt = datetime.fromtimestamp(obs.get('timeStamp', 0))
                line = dt.strftime(self._date_time_format)

                if obs.get('id') is not None:
                    line += self._separator + obs.get('id')

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

                self.logger.info('Saved observation "{}" with ID "{}" from '
                                 'port "{}" to file "{}"'
                                 .format(obs.get('name'),
                                         obs.get('id'),
                                         obs.get('portName'),
                                         path + file_name))

        return obs


class RealTimePublisher(Prototype):
    """
    RealTimePublisher sends copies of `Observation` objects to a list of
    receivers.
    """

    def __init__(self, name, type, manager):
        Prototype.__init__(self, name, type, manager)
        config = self._config_manager.get(self._name)

        self._receivers = config.get('receivers')
        self._is_enabled = config.get('enabled')

    def process_observation(self, obs):
        if not self._is_enabled:
            return obs

        for receiver in self._receivers:
            obs_copy = copy.deepcopy(obs)

            target = receiver + '/' + obs_copy.get('id')

            obs_copy.set('nextReceiver', 0)
            obs_copy.set('receivers', [target])

            self.logger.debug('Publishing observation "{}" with ID "{}" to "{}"'
                              .format(obs_copy.get('name'),
                                      obs_copy.get('id'),
                                      target))

            header = {'type': 'observation'}
            payload = obs_copy.data

            self.publish(target, header, payload)

        return obs
