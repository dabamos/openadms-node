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
import os
import time

from datetime import datetime
from enum import Enum

from modules import prototype

"""Module for the export of sensor data to files and databases."""

logger = logging.getLogger('openadms')


class FileRotation(Enum):

    """
    Enumeration of file rotation times of flat files.
    """

    NONE = 0
    DAILY = 1
    MONTHLY = 2
    YEARLY = 3


class FileExporter(prototype.Prototype):

    """
    Exports sensor data to a flat file in CSV format.
    """

    def __init__(self, name, config_manager, sensor_manager):
        prototype.Prototype.__init__(self, name, config_manager,
                                     sensor_manager)
        config = self._config_manager.config['FileExporter']
        self._file_extension = config['FileExtension']
        self._file_name = config['FileName']
        self._file_rotation = {
            'none': FileRotation.NONE,
            'daily': FileRotation.DAILY,
            'monthly': FileRotation.MONTHLY,
            'yearly': FileRotation.YEARLY}[config['FileRotation']]
        self._date_time_format = config['DateTimeFormat']
        self._separator = config['Separator']
        self._paths = self._revise_paths(config['Paths'])

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

    def action(self, obs):
        """Append data to a flat file in CSV format.

        Args:
            obs(Observation): The input observation object.

        Returns:
            obs(Observation): The output observation object.
        """
        ts = datetime.fromtimestamp(obs.get('TimeStamp'))

        date = {
            # No file rotation, i.e., all data is stored in a single file.
            FileRotation.NONE: None,
            # Every day a new file is created.
            FileRotation.DAILY: ts.strftime('%Y-%m-%d'),
            # Every month a new file is created.
            FileRotation.MONTHLY: ts.strftime('%Y-%m'),
            # Every year a new file is created.
            FileRotation.YEARLY: ts.strftime('%Y')}[self._file_rotation]

        file_name = self._file_name
        file_name = file_name.replace('{port}', obs.get('PortName'))
        file_name = file_name.replace('{date}', '{}'.format(date)
                                      if date else '')
        file_name = file_name.replace('{id}', '{}'.format(obs.get('ID'))
                                      if obs.get('ID') is not None else '')
        file_name += self._file_extension

        for path in self._paths:
            if not os.path.isdir(path):
                logger.error('Path "{}" does not exist'.format(path))
                continue

            # Create a header if a new file has to be touched.
            header = None

            if not os.path.isfile(path + file_name):
                header = '# Target "{}" of "{}" on "{}"\n' \
                         .format(obs.get('ID'),
                                 obs.get('SensorName'),
                                 obs.get('PortName'))
            # Open a file for every path.
            with open(path + file_name, 'a') as fh:
                # Add the header if necessary.
                if header:
                    fh.write(header)

                # Convert Unix time stamp to date and time.
                dt = datetime.fromtimestamp(obs.get('TimeStamp'))
                line = dt.strftime(self._date_time_format)

                try:
                    if obs.get('ID') is not None:
                        line += self._separator + obs.get('ID')

                    for response in obs.get('ResponseSets'):
                        d = response['Description']
                        v = response['Value']
                        u = response['Unit']

                        line += self._separator + format(d)
                        line += self._separator + format(v)
                        line += self._separator + format(u)
                except KeyError:
                    logger.warning('Observation "{}" of sensor "{}" on '
                                   'port "{}" is incomplete'
                                   .format(obs.get('Name'),
                                           obs.get('SensorName'),
                                           obs.get('PortName')))

                # Write line to file.
                fh.write(line + '\n')

                logger.info('Saved observation "{}" from port "{}" to file '
                            '"{}"'.format(obs.get('Name'),
                                          obs.get('PortName'),
                                          path + file_name))

        return obs
