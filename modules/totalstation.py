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

import hashlib
import logging
import math
import re
import time

from core.sensor import SensorType
from modules import prototype

"""Module for data processing (pre-precessing, atmospheric corrections,
transformations)."""

logger = logging.getLogger('openadms')


class DistanceCorrector(prototype.Prototype):

    """Corrects the slope distance for EDM measurements using atmospheric
    data."""

    def __init__(self, name, config_manager, sensor_manager):
        prototype.Prototype.__init__(self, name, config_manager,
                                     sensor_manager)

        config = self._config_manager.config.get(self._name)

        # Maximum age of atmospheric data.
        self._max_age = 3600
        # TODO ... maybe should be better part of the configuration?

        self._is_atmospheric_correction = \
            config.get('AtmosphericCorrectionEnabled')
        self._is_sealevel_correction = \
            config.get('SealevelCorrectionEnabled')

        self.temperature = config.get('Temperature')
        self.pressure = config.get('Pressure')
        self.humidity = config.get('Humidity')
        self.sensor_height = config.get('SensorHeight')

        self.last_update = time.time()

    def action(self, obs):
        sensor_type = obs.get('SensorType')

        # Update atmospheric data if sensor is a weather station.
        if SensorType.is_weather_station(sensor_type):
            self._update_meteorological_data(obs)
            return obs

        # Check if sensor is of type "total station".
        if not SensorType.is_total_station(sensor_type):
            logger.warning('Sensor type "{}" not supported'.format(sensor_type))
            return obs

        # Check if atmospheric data has been set.
        if not self.temperature or not self.pressure or not self.humidity:
            logger.warning('Temperature, air pressure, or humidity missing')
            return obs

        # Check the age of the atmospheric data.
        if self.last_update - time.time() > self._max_age:
            logger.warning('Atmospheric data is older than {} hour(s)'
                           .format(int(max_age / 3600)))

        # Reduce the slope distance of the EDM measurement if the sensor is a
        # robotic total station.
        dists = obs.find('ResponseSets', 'Description', 'SlopeDist')
        dist = None

        if len(dists) > 0:
            dist = dists[0].get('Value')
        else:
            logger.warning('SlopeDist is missing in observation "{}"'
                           .format(obs.get('Name')))
            return

        if dist is None:
            logger.warning('SlopeDist value is missing in observation "{}"'
                           .format(obs.get('Name')))
            return

        d_dist_1 = 0
        d_dist_2 = 0

        response_sets = obs.get('ResponseSets')

        # Calculate the atmospheric reduction of the distance.
        if self._is_atmospheric_correction:
            ppm = self.get_ppm()
            d_dist_1 = dist * ppm * math.pow(10, -6)

            logger.debug('Reduced distance from {} m to {} m ({} ppm)'
                         .format(round(dist, 5),
                                 round(dist + d_dist_1, 5),
                                 round(ppm, 2)))

            response_ppm = self._get_response_set('PPM',
                                                  'Float',
                                                  'none',
                                                  round(ppm, 5))
            response_sets.append(response_ppm)

        # Calculate the sealevel reduction of the distance.
        if self._is_sealevel_correction:
            earth_radius = 6.378 * math.pow(10, 6)

            # Delta distance: -(height / R) * 10^6
            d_dist_2 = -1 * (self.sensor_height / earth_radius)

            logger.debug('Reduced distance to mean sea level from {} m to '
                         '{} m ({} m)'.format(round(dist, 5),
                                              round(dist + d_dist_2, 5),
                                              round(d_dist_2, 5)))

            response_sealevel = self._get_response_set('SealevelDelta',
                                                         'Float',
                                                         'm',
                                                         round(d_dist_2, 5))
            response_sets.append(response_sealevel)

        # Add reduced distance to the observation set.
        if d_dist_1 != 0 or d_dist_2 != 0:
            r_dist = dist + d_dist_1 + d_dist_2

            logger.info('Reduced distance from {} m to {} m ({} m)'
                        .format(round(dist, 5),
                                round(r_dist, 5),
                                round(d_dist_2 + d_dist_2, 5)))

            response_r_dist = self._get_response_set('ReducedDist',
                                                     'Float',
                                                     'm',
                                                     round(r_dist, 5))
            response_sets.append(response_r_dist)

        return obs


    def get_ppm(self):
        """Calculates the atmospheric correction value in parts per million
        (ppm) for the reduction of distances gained by electronic distance
        measurement (EDM).

        The formulas are taken from the official manual of the Leica TM30
        robotic total station. They should be valid for all modern total
        stations of Leica Geosystems. For further information, please see Leica
        TM30 manual on page 76."""
        alpha = 1 / 273.15
        div = (1 + alpha * self.temperature)
        x = (7.5 * self.temperature / (237.3 + self.temperature)) + 0.7857

        s1 = 0.29525 * self.pressure
        s2 = 4.126 * math.pow(10, -4) * self.humidity

        ppm = 286.34 - ((s1 / div) - ((s2 / div) * math.pow(10, int(x))))

        return ppm

    def _update_meteorological_data(self, obs):
        """Updates the temperature, air pressure, and humidity attributes by
        using the measured data of a weather station."""
        temperatures = obs.find('ResponseSets', 'Description', 'Temperature')
        pressures = obs.find('ResponseSets', 'Description', 'Pressure')
        humidities = obs.find('ResponseSets', 'Description', 'Humidity')

        if len(temperatures) > 0:
            self.temperature = temperatures[0].get('Value')

        if len(pressures) > 0:
            self.pressure = pressures[0].get('Value')

        if len(humidities) > 0:
            if humidities[0].get('Unit') == '%':
                self.humidity = humidities[0].get('Value') / 100
            else:
                self.humidity = humidities[0].get('Value')

    def _get_response_set(self, d, t, u, v):
        r = {}

        r['Description'] = d
        r['Type'] = t
        r['Unit'] = u
        r['Value'] = v

        return r

    @property
    def temperature(self):
        return self._temperature

    @property
    def pressure(self):
        return self._pressure

    @property
    def humidity(self):
        return self._humidity

    @property
    def last_update(self):
        return self._last_update

    @property
    def sensor_height(self):
        return self._sensor_height

    @temperature.setter
    def temperature(self, temperature):
        """Sets the temperature."""
        self._temperature = temperature
        self._last_update = time.time()

        if temperature:
            logger.info('Updated temperature to {} C'
                        .format(round(temperature, 2)))

    @pressure.setter
    def pressure(self, pressure):
        """Sets the air pressure."""
        self._pressure = pressure
        self._last_update = time.time()

        if pressure:
            logger.info('Updated pressure to {} hPa'
                        .format(round(pressure, 2)))

    @humidity.setter
    def humidity(self, humidity):
        """Sets the humidity."""
        self._humidity = humidity
        self._last_update = time.time()

        if humidity:
            logger.info('Updated humidity to {}'
                        .format(round(humidity, 2)))

    @last_update.setter
    def last_update(self, last_update):
        self._last_update = last_update

    @sensor_height.setter
    def sensor_height(self, sensor_height):
        self._sensor_height = sensor_height


class SerialMeasurementProcessor(prototype.Prototype):

    def __init__(self, name, config_manager, sensor_manager):
        prototype.Prototype.__init__(self, name, config_manager,
                                     sensor_manager)

        config = self._config_manager.config[self._name]

        self._max_faces = config['MaximumFaces']
        self._prior_observations = {}

    def _add(self, obs):
        md5 = self._get_md5(obs)
        self._first_faces[md5] = obs

    def _average_vertical_angles(self, obs_1, obs_2):
        response_sets1 = obs_1.get('ResponseSets')
        response_sets2 = obs_2.get('ResponseSets')

        v1 = None
        v2 = None

        dist1 = None
        dist2 = None

        for response1, response2 in zip(response_sets1, response_sets2):
            desc1 = r1.get('Description').lower()
            desc2 = r2.get('Description').lower()

            value1 = r1.get('Value')
            value2 = r2.get('Value')


            if set([desc1, desc2]).issubset(['v', 'vertical']):
                v1 = value1
                v2 = value2

            if set([desc1, desc2]).issubset(['dist', 'slopedist']):
                dist1 = value1
                dist2 = value2

            if set([desc1, desc2]).issubset(['reduceddist', 'reduceddistance']):
                dist1 = value1
                dist2 = value2

        if v1 is None or v2 is None or dist1 is None or dist2 is None:
             logger.error('Observation "{}" is incomplete'
                          .format(obs.get('Name')))
             return

        k = (2 * math.pi - (v1 + v2)) / 2

        accurate_v1 = v1 + k
        accurate_v2 = v2 + k

        accurate_dist = (dist1 + dist2) / 2

        return accurate_v1, accurate_v2, accurate_dist


    def _get_first(self, obs):
        md5 = self._get_md5(obs)
        first = self._first_faces.get(md5)
        return first

    def _get_md5(self, obs):
        s1 = obs.get('PortName')
        s2 = obs.get('SensorName')
        s3 = obs.get('ID')

        value = ''.join([s1, s2, s3])
        md5 = hashlib.md5(value.encode('utf-8')).hexdigest()
        return md5

    def _is_valid(self, obs):
        sensor_type = obs.get('SensorType')
        face = obs.get('Face')

        if not SensorType.is_total_station(sensor_type):
            logger.warning('Sensor type "{}" is not supported'
                           .format(sensor_type))
            return False

        if face is None:
            logger.error('Observation "{}" has no face'
                         .format(obs.get('Name')))
            return False

        if face not in [1, 2]:
            logger.error('Face "{}" is not valid'.format(face))
            return False

        return True

    def action(self, obs):
        if not self._is_valid(obs):
            return obs

        face = obs.get('Face')

        if face == 1:
            self._add(obs)

        if face == 2:
            first = self._get_first(obs)

            if first is None:
                logger.error('First face of observation "{}" not found'
                             .format(obs.get('Name')))
                return obs

        return obs


class HelmertTransformer(prototype.Prototype):

    """
    Calculates a 3-dimensional coordinates of a view point using the Helmert
    transformation.
    """

    def __init__(self, name, config_manager, sensor_manager):
        prototype.Prototype.__init__(self, name, config_manager,
                                     sensor_manager)
        config = self._config_manager.config[self._name]

    def action(self, obs):
        return obs


class PolarTransformer(prototype.Prototype):

    """
    Calculates 3-dimensional coordinates of a target using the sensor position,
    and the azimuth position from the configuration together with the
    horizontal direction, the vertical angle, and the distance of a total
    station observation. The result (Y, X, Z) is added to the observation data
    set.
    """

    def __init__(self, name, config_manager, sensor_manager):
        prototype.Prototype.__init__(self, name, config_manager,
                                     sensor_manager)
        config = self._config_manager.config[self._name]

        self._sensor_y = config.get('SensorPosition').get('East')
        self._sensor_x = config.get('SensorPosition').get('North')
        self._sensor_z = config.get('SensorPosition').get('Height')

        self._azimuth_y = config.get('AzimuthPosition').get('East')
        self._azimuth_x = config.get('AzimuthPosition').get('North')

    def action(self, obs):
        sensor_type = obs.get('SensorType')

        if not SensorType.is_total_station(sensor_type.lower()):
            logger.error('Sensor type "{}" is not supported'
                         .format(sensor_type))
            return obs

        hzs = obs.find('ResponseSets', 'Description', 'Hz')
        vs = obs.find('ResponseSets', 'Description', 'V')
        dists = obs.find('ResponseSets', 'Description', 'SlopeDist')
        r_dists = obs.find('ResponseSets', 'Description', 'ReducedDist')

        hz = v = dist = None

        # Set Hz, V, and distance.
        if len(hzs) > 0 and len(vs) > 0 and len(dists) > 0:
            hz = hzs[0].get('Value')        # Hz direction.
            v = vs[0].get('Value')          # V angle.
            dist = dists[0].get('Value')    # Slope distance.
        else:
            logger.warning('Responses of observation "{}" are incomplete'
                           .format(obs.get('Name')))

        # Override distance with reduced distance.
        if len(r_dists) > 0:
            dist = r_dists[0]['Value']
        else:
            logger.warning('Distance has not been reduced')

        if hz is None or v is None or dist is None:
            logger.error('Responses of observation "{}" are incomplete'
                         .format(obs.get('Name')))
            return obs

        # Radiant to grad (gon).
        hz_grad = hz * 200 / math.pi
        v_grad = v * 200 / math.pi

        logger.debug('Starting polar transformation of target "{}" with '
                     '[Hz = {:3.5f} gon, V = {:3.5f} gon, dist = {:4.5f} m]'
                     .format(obs.get('ID'),
                             hz_grad,
                             v_grad,
                             dist))

        (y, x, z) = self.transform(self._sensor_x,
                                   self._sensor_y,
                                   self._sensor_z,
                                   self._azimuth_x,
                                   self._azimuth_y,
                                   hz,
                                   v,
                                   dist)

        logger.info('Transformed target "{}" to [Y = {:3.4f}, '
                    'X = {:3.4f}, Z = {:3.4f}]'.format(obs.get('ID'),
                                                       y,
                                                       x,
                                                       z))

        # Create dictionaries (name, type, unit, value).
        response_y = self._create_response_set('Y', 'Float', 'm', round(y, 5))
        response_x = self._create_response_set('X', 'Float', 'm', round(x, 5))
        response_z = self._create_response_set('Z', 'Float', 'm', round(z, 5))

        # Add to observation data set.
        response_sets = obs.get('ResponseSets')
        response_sets.append(response_y)
        response_sets.append(response_x)
        response_sets.append(response_z)

        return obs

    def transform(self, sensor_x, sensor_y, sensor_z, azimuth_x, azimuth_y, hz,
                  v, dist):
        """Calculates coordinates (Y, X, Z) out of horizontal direction,
        vertical angle, and slope distance to a target point by doing a
        3-dimensional polar transformation."""
        # Calculate azimuth angle from coordinates.
        if azimuth_x == sensor_x:
            # Because arctan(0) = 0.
            azimuth_angle = 0
        else:
            azimuth_angle = math.atan((azimuth_y - sensor_y) /
                                      (azimuth_x - sensor_x))

        point_angle = azimuth_angle + hz

        # Calculate coordinates of the new point.
        d_y = dist * math.sin(v) * math.sin(point_angle)
        d_x = dist * math.sin(v) * math.cos(point_angle)
        d_z = dist * math.cos(v)

        x = sensor_x + d_x
        y = sensor_y + d_y
        z = sensor_z + d_z

        return (y, x, z)

    def _create_response_set(self, d, t, u, v):
        response = {}

        response['Description'] = d
        response['Type'] = t
        response['Unit'] = u
        response['Value'] = v

        return response
