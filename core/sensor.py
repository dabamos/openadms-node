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

from core import observation

logger = logging.getLogger('openadms')


class Sensor(object):

    """
    Sensor stores the configuration of a sensor, including all used commands.
    """

    def __init__(self, name, config_manager):
        self._name = name
        self._config_manager = config_manager

        config = self._config_manager.config['Sensors'][self._name]
        self._type = config['Type']

        # Create a dictionary of observation data.
        self._observation_sets = {}

        for set_name, observations in config['Observations'].items():
            local_set = []

            # Add all commands of the observations set to the list.
            for observation in observations:
                obs = self.get_observation_data(observation)

                local_set.append(obs)
                # logger.debug('Added observation "{}" to observation '
                #             'set "{}" of sensor {}'
                #             .format(obs.get('Name'), set_name, name))

            if len(local_set) > 0:
                self._observation_sets[set_name] = local_set
                logger.debug('Loaded observation set "{}" of sensor "{}"'
                             .format(set_name, self._name))

    def get_observation_set(self, set_name):
        return self._observation_sets[set_name]

    def get_observation_data(self, data):
        """Creates an observation data object."""
        data['SensorName'] = self._name
        data['SensorType'] = self._type

        # Character '\' is escaped in JSON file.
        data['ResponsePattern'] = data['ResponsePattern'].replace('\\\\', '\\')

        return observation.Observation(data)

    @property
    def name(self):
        return self._name


class SensorType(object):

    # Acronyms of valid sensor types:
    #
    # RTS: Robotic Total Station
    # TPS: Tachymeter-Positionierungssystem
    # TST: Total Station Theodolite
    total_stations = ['rts', 'tachymeter', 'total station', 'totalstation',
                      'tps', 'tst']
    weather_stations = ['meteo', 'meteorological', 'meteorological sensor',
                        'meteorological station', 'weather', 'weather station',
                        'weatherstation']

    @staticmethod
    def is_total_station(name):
        if name in SensorType.total_stations:
            return True

        return False

    @staticmethod
    def is_weather_station(name):
        if name in SensorType.weather_stations:
            return True

        return False
