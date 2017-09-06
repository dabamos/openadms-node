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

import codecs
import logging
import uuid

from typing import *

from core.observation import Observation


class Sensor(object):
    """
    Sensor stores the configuration of a sensor, especially, all defined
    observations.
    """

    def __init__(self, name: str, config: Dict[str, Any]):
        """
        Args:
            name: The name of the sensor.
            config: The configuration of the sensor.
        """
        self.logger = logging.getLogger(name)

        self._name = name
        self._config = config
        self._type = self._config.get('type')
        self._description = self._config.get('description', '')

        self._observations = {}

        for data in self._config.get('observations'):
            obs = self.create_observation(data)
            self._observations[obs.get('name')] = obs

            self.logger.debug('Loaded observation "{}" of sensor "{}"'
                              .format(obs.get('name'), self._name))

    def create_observation(self, data: Dict[str, Any]) -> Observation:
        """Creates an observation object.

        Args:
            data: The observation data.
        """
        data['id'] = Observation.get_new_id()
        data['sensorName'] = self._name
        data['sensorType'] = self._type

        # Character '\' is escaped in the JSON configuration file. Encoded
        # bytes have to be decoded.
        for set_name, request_set in data.get('requestSets').items():
            if request_set.get('request'):
                request_set['request'] = codecs.decode(
                        request_set.get('request'),
                        'unicode_escape'
                )

            if request_set.get('responseDelimiter'):
                request_set['responseDelimiter'] = codecs.decode(
                        request_set.get('responseDelimiter'),
                        'unicode_escape'
                )

            if request_set.get('responsePattern'):
                request_set['responsePattern'] = codecs.decode(
                        request_set.get('responsePattern'),
                        'unicode_escape'
                )

        return Observation(data)

    def get_observation(self, name: str) -> None:
        """Returns a single observation.

        Args:
            name: The name of the observation.
        """
        return self._observations.get(name)

    def get_observations(self) -> Dict[str, Observation]:
        """Returns all observations.

        Returns:
            Dictionary with observation objects.
        """
        return self._observations

    @property
    def description(self) -> str:
        return self._description

    @property
    def name(self) -> str:
        return self._name

    @property
    def type(self) -> str:
        return self._type


class SensorType(object):
    """
    SensorType is a static class used to determine the type of a sensor.
    """

    # Acronyms of valid sensor types:
    #
    # RTS: Robotic Total Station
    # TPS: Total Station Positioning System
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
    def is_total_station(name: str) -> bool:
        """Returns whether or not the given name is a total station or not.

        Returns:
            True if name is a total station, False if not.
        """
        if name.lower() in SensorType.total_stations:
            return True

        return False

    @staticmethod
    def is_weather_station(name: str) -> bool:
        """Returns whether or not the given name is a weather station or not.

        Returns:
            True if name is a weather station, False if not.
        """
        if name.lower() in SensorType.weather_stations:
            return True

        return False
