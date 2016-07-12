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

import itertools
import logging
import os
import time

from datetime import datetime
from enum import Enum

from modules import prototype

"""Module for the export of sensor data to files and databases."""

logger = logging.getLogger('netadms')


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

    def __init__(self, name, config_manager):
        prototype.Prototype.__init__(self, name, config_manager)

        self._config_manager = config_manager
        root = self._config_manager.config['FileExporter']

        self._file_extension = root['FileExtension']
        self._file_rotation = {
            'none': FileRotation.NONE,
            'daily': FileRotation.DAILY,
            'monthly': FileRotation.MONTHLY,
            'yearly': FileRotation.YEARLY}[root['FileRotation']]
        self._date_time_format = root['DateTimeFormat']
        self._separator = root['Separator']

        self._paths = self._check_paths(root['Paths'])

    def _check_paths(self, paths):
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

    def action(self, obs_data):
        """Append data to a flat file in CSV format.

        Args:
            obs_date(ObservationData): The input observation data object.

        Returns:
            obs_data(ObservationData): The output observation data object.
        """
        ts = datetime.fromtimestamp(obs_data.get('TimeStamp'))

        date = {
            # No file rotation, i.e., all data is stored in a single file.
            FileRotation.NONE: None,
            # Every day a new file is created.
            FileRotation.DAILY: ts.strftime('%Y-%m-%d'),
            # Every month a new file is created.
            FileRotation.MONTHLY: ts.strftime('%Y-%m'),
            # Every year a new file is created.
            FileRotation.YEARLY: ts.strftime('%Y')}[self._file_rotation]

        # File name: consists of interface name, current date, and
        # file extension.
        file_name = obs_data.get('PortName')
        file_name += '_{}'.format(date) if date is not None else ''
        file_name += self._file_extension

        # Create a header if a new file has to be touched.
        header = None

        if not os.path.isfile(file_name):
            header = '# {} on {}\n'.format(obs_data.get('SensorName'),
                                           obs_data.get('PortName'))

        for path in self._paths:
            # Open a file for every path.
            with open(path + file_name, 'a') as fh:
                # Add the header if necessary.
                if header is not None:
                    fh.write(header)

                # Convert Unix time stamp to date and time.
                dt = datetime.fromtimestamp(obs_data.get('TimeStamp'))
                line = dt.strftime(self._date_time_format)

                for query in obs_data.get('Queries'):
                    try:
                        if query['ID'] is not None:
                            line += self._separator + query['ID']

                        descriptions = query['ResponseDescriptions']
                        values = query['ResponseValues']
                        units = query['ResponseUnits']

                        # Add values and units to the line.
                        for d, v, u in itertools.zip_longest(descriptions,
                            values, units):
                            line += self._separator + format(d)
                            line += self._separator + format(v)
                            line += self._separator + format(u)
                    except KeyError:
                        logger.error('Observation data set of sensor "{}" on '
                                     'port "{}" is incomplete'
                                     .format(obs_data.get('SensorName'),
                                             obs_data.get('PortName')))
                        continue

                fh.write(line + '\n')

                logger.info('Saved observation data from port "{}" to file '
                            '"{}"'.format(obs_data.get('PortName'),
                                          path + file_name))

        return obs_data

    def destroy(self, *args):
        pass
