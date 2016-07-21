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
import math
import re
import time

from modules import prototype

"""Module for data processing (pre-precessing, atmospheric corrections,
transformations)."""

logger = logging.getLogger('openadms')


class DistanceCorrector(prototype.Prototype):

    def __init__(self, name, config_manager):
        prototype.Prototype.__init__(self, name, config_manager)
        self._config_manager = config_manager
        config = self._config_manager.config[self._name]

        # Valid weather station types.
        self._ws_types = ['meteo', 'meteorological', 'meteorological station',
                          'weather', 'weather station', 'weatherstation']
        # Valid total station types.
        self._ts_types = ['rts', 'tachymeter', 'total station',
                          'totalstation', 'tps', 'tst']
        # Maximum age of atmospheric data.
        self._max_age = 3600
        # TODO ... maybe should be better part of the configuration?

        self._is_atmospheric_correction = config[
            'AtmosphericCorrectionEnabled']
        self._is_sealevel_correction = config['SealevelCorrectionEnabled']

        try:
            self.temperature = config['Temperature']
            self.pressure = config['Pressure']
            self.humidity = config['Humidity']
            self.sensor_height = config['SensorHeight']

            self.last_update = time.time()
        except KeyError:
            debug.error('Configuration is invalid')

    def action(self, obs_data):
        sensor_type = obs_data.get('SensorType').lower()

        # Check sensor type.
        if (sensor_type not in self._ws_types) and \
                (sensor_type not in self._ts_types):
            logger.warning('Wrong sensor type ("{}")'.format(sensor_type))
            return obs_data

        # Update atmospheric data if sensor is a weather station.
        if sensor_type in self._ws_types:
            self._update_meteorological_data(obs_data)
            return obs_data

        # Check if atmospheric data has been set.
        if self.temperature == None or self.pressure == None or \
                self.humidity == None:
            logger.warning('Temperature, air pressure, or humidity missing')
            return obs_data

        # Check the age of the atmospheric data.
        if self.last_update - time.time() > self._max_age:
            logger.warning('Atmospheric data is older than {} hour(s)'
                           .format(int(max_age / 3600)))

        # Reduce the slope distance of the EDM measurement if the sensor is a
        # robotic total station.
        dist = None
        response_sets = obs_data.get('ResponseSets')

        # Search for slope distance.
        for response in response_sets:
            try:
                d = response['Description'].lower()
                v = response['Value']

                if d in ['dist', 'slopedist']:
                    dist = v
                    break
            except KeyError:
                logger.warning('Data missing in response set of '
                               'observation "{}"'
                               .format(obs_data.get('Name')))

        if dist == None:
            logger.warning('No slope distance found for reduction')
            return obs_data

        d_dist_1 = 0
        d_dist_2 = 0

        # Calculate the atmospheric reduction of the distance.
        if self._is_atmospheric_correction:
            ppm = self.get_ppm()
            d_dist_1 = dist * ppm * math.pow(10, -6)

            logger.debug('Reduced distance to atmosphere from {} m to '
                         '{} m ({} ppm)'.format(round(dist, 5),
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

        return obs_data

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

    def _update_meteorological_data(self, obs_data):
        """Updates the temperature, air pressure, and humidity attributes by
        using the measured data of a weather station."""
        response_sets = obs_data.get('ResponseSets')

        for response in response_sets:
            try:
                d = response['Description'].lower()
                u = response['Unit']
                v = response['Value']

                # Temperature.
                if d in ['temp', 'temperature']:
                    self.temperature = v
                    continue

                # Air pressure.
                if d in ['airpressure', 'press', 'pressure']:
                    self.pressure = v
                    continue

                # Humidity.
                if d in ['humidity', 'moisture']:
                    if u == '%':
                        # Unit is percent (e.g., 75 %).
                        self.humidity = v / 100
                    else:
                        # No unit (e.g., 0.75).
                        self.humidity = v
            except KeyError:
                logger.warning('Data missing in response set of '
                               'observation "{}"'
                               .format(obs_data.get('Name')))


    def _get_response_set(self, d, t, u, v):
        response = {}

        response['Description'] = d
        response['Type'] = t
        response['Unit'] = u
        response['Value'] = v

        return response

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

        if temperature is not None:
            logger.info('Updated temperature to {} C'
                        .format(round(temperature, 2)))

    @pressure.setter
    def pressure(self, pressure):
        """Sets the air pressure."""
        self._pressure = pressure
        self._last_update = time.time()

        if pressure is not None:
            logger.info('Updated pressure to {} hPa'
                        .format(round(pressure, 2)))

    @humidity.setter
    def humidity(self, humidity):
        """Sets the humidity."""
        self._humidity = humidity
        self._last_update = time.time()

        if humidity is not None:
            logger.info('Updated humidity to {}'
                        .format(round(humidity, 2)))

    @last_update.setter
    def last_update(self, last_update):
        self._last_update = last_update

    @sensor_height.setter
    def sensor_height(self, sensor_height):
        self._sensor_height = sensor_height

    def destroy(self, *args):
        pass


class HelmertTransformer(prototype.Prototype):

    """
    Calculates a 3-dimensional coordinates of a view point using the Helmert
    transformation.
    """

    def __init__(self, name, config_manager):
        prototype.Prototype.__init__(self, name, config_manager)
        config = self._config_manager.config[self._name]

    def action(self, obs_data):
        return obs_data

    def destroy(self, *args):
        pass


class PolarTransformer(prototype.Prototype):

    """
    Calculates 3-dimensional coordinates of a target using the sensor position,
    and the azimuth position from the configuration together with the
    horizontal direction, the vertical angle, and the distance of a total
    station observation. The result (Y, X, Z) is added to the observation data
    set.
    """

    def __init__(self, name, config_manager):
        prototype.Prototype.__init__(self, name, config_manager)
        config = self._config_manager.config[self._name]

        # Acronyms of valid sensor types:
        #
        # RTS: Robotic Total Station
        # TPS: Tachymeter-Positionierungssystem
        # TST: Total Station Theodolite
        self._valid_types = ['rts', 'tachymeter', 'total station',
                             'totalstation', 'tps', 'tst']

        self._sensor_y = config['SensorPosition']['East']
        self._sensor_x = config['SensorPosition']['North']
        self._sensor_z = config['SensorPosition']['Height']

        self._azimuth_y = config['AzimuthPosition']['East']
        self._azimuth_x = config['AzimuthPosition']['North']

    def action(self, obs_data):
        # Check the configuration for the given sensor port.
        port_name = obs_data.get('PortName')
        sensor_type = obs_data.get('SensorType').lower()
        response_sets = obs_data.get('ResponseSets')

        if not sensor_type in self._valid_types:
            logger.error('Sensor is not of type "total station"')
            return obs_data

        hz = None
        v = None
        dist = None
        r_dist = None

        # Search for Hz, V, and reduced/slope distance from the observation
        # data set.
        for response in response_sets:
            try:
                description = response['Description'].lower()
                value = response['Value']

                # Horizontal direction.
                if description in ['hz', 'horizontal']:
                    hz = value

                # Vertical angle.
                if description in ['v', 'vertical']:
                    v = value

                # Slope distance if no reduced distance is set.
                if description in ['dist', 'slopedist']:
                    dist = value

                # Reduced distance.
                if description in ['reduceddist', 'reduceddistance']:
                    r_dist = value
            except KeyError:
                logger.warning('Data missing in response set of '
                               'observation "{}"'
                               .format(obs_data.get('Name')))

        if hz == None or v == None or dist == None:
            logger.error('Observation is incomplete '
                         '(Hz, V, or distance is missing)')
            return obs_data

        # Override slope distance with reduced distance.
        if r_dist == None:
            logger.warning('No reduced distance set')
        else:
            dist = r_dist

        # Radiant to grad (gon).
        hz_grad = hz * 200 / math.pi
        v_grad = v * 200 / math.pi

        logger.debug('Starting polar transformation of target "{}" with '
                     '[Hz = {:3.5f} gon, V = {:3.5f} gon, dist = {:4.5f} m]'
                     .format(obs_data.get('ID'),
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
                    'X = {:3.4f}, Z = {:3.4f}]'.format(obs_data.get('ID'),
                                                       y,
                                                       x,
                                                       z))

        # Create dictionaries (name, type, unit, value).
        response_y = self._get_response_set('Y', 'Float', 'm', round(y, 5))
        response_x = self._get_response_set('X', 'Float', 'm', round(x, 5))
        response_z = self._get_response_set('Z', 'Float', 'm', round(z, 5))

        # Add to observation data set.
        response_sets.append(response_y)
        response_sets.append(response_x)
        response_sets.append(response_z)

        return obs_data

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

    def _get_response_set(self, d, t, u, v):
        response = {}

        response['Description'] = d
        response['Type'] = t
        response['Unit'] = u
        response['Value'] = v

        return response

    def destroy(self, *args):
        pass
