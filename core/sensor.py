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

from core.observation import Observation

logger = logging.getLogger('openadms')


class Sensor(object):

    """
    Sensor stores the configuration of a sensor, including all used commands.
    """

    def __init__(self, name, config_manager):
        self._name = name
        self._config_manager = config_manager

        config = self._config_manager.config.get('sensors').get(self._name)
        self._type = config.get('type')
        self._observations = {}

        for data in config.get('observations'):
            obs = self._create_observation(data)
            self._observations[obs.get('name')] = obs
            logger.debug('Loaded observation "{}" of sensor "{}"'
                         .format(obs.get('name'), self._name))

    def get_observation(self, name):
        """Returns a single observation."""
        return self._observations.get(name)

    def get_observations(self):
        """Returns all observations."""
        return self._observations

    def _create_observation(self, data):
        """Creates an observation object."""
        data['sensorName'] = self._name
        data['sensorType'] = self._type

        # Character '\' is escaped in the JSON configuration file.
        for set_name, request_set in data.get('requestSets').items():
            request_set['responsePattern'] = (request_set['responsePattern']
                .replace('\\\\', '\\'))

        return Observation(data)

    @property
    def name(self):
        return self._name


class SensorType(object):

    # Acronyms of valid sensor types:
    #
    # RTS: Robotic Total Station
    # TPS: Tachymeter-Positionierungssystem
    # TST: Total Station Theodolite
    total_stations = ['rts',
                      'tachymeter',
                      'totalstation',
                      'tps',
                      'tst']

    weather_stations = ['meteo',
                        'meteorologicalsensor',
                        'meteorologicalstation',
                        'weatherstation']

    @staticmethod
    def is_total_station(name):
        if name.lower() in SensorType.total_stations:
            return True

        return False

    @staticmethod
    def is_weather_station(name):
        if name.lower() in SensorType.weather_stations:
            return True

        return False
