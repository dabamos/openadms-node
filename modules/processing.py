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

logger = logging.getLogger('netadms')


class AtmosphericCorrector(prototype.Prototype):

    def __init__(self, name, config_manager):
        prototype.Prototype.__init__(self, name, config_manager)
        # self._config = self._config_manager.config[self._name]

        # Valid weather station types.
        self._ws_types = ['meteo', 'meteorological', 'meteorological station',
                          'weather', 'weather station', 'weatherstation']
        # Valid total station types.
        self._ts_types = ['rts', 'tachymeter', 'total station',
                          'totalstation', 'tps', 'tst']

        self._temperature = None
        self._pressure = None
        self._humidity = None
        self._last_update = None

    def _reduce_distance(self, obs_data, ppm):
        descriptions = obs_data.get('ResponseDescriptions')
        values = obs_data.get('ResponseValues')

        dist = None

        for i in range(len(descriptions)):
            d = descriptions[i].lower()

            # Search for slope distance.
            if d in ['dist', 'slopedist']:
                dist = values[i]
                break

        if dist == None:
            logger.warning('No slope distance found for reduction')
            return obs_data

        # Reduce distance with given ppm value.
        r_dist = dist + ((ppm * math.pow(10, -6)) * dist)

        logger.debug('Reduced distance from {} m to {} m ({} ppm)'
                     .format(round(dist, 4),
                             round(r_dist, 4),
                             round(ppm, 1)))

        # Add PPM value.
        obs_data.data['ResponseDescriptions'].append('ppm')
        obs_data.data['ResponseValues'].append(round(ppm, 5))
        obs_data.data['ResponseUnits'].append('none')

        # Add reduced distance.
        obs_data.data['ResponseDescriptions'].append('ReducedDist')
        obs_data.data['ResponseValues'].append(round(r_dist, 5))
        obs_data.data['ResponseUnits'].append('m')

        return obs_data

    def _update_meteorological_data(self, obs_data):
        descriptions = obs_data.get('ResponseDescriptions')
        values = obs_data.get('ResponseValues')
        units = obs_data.get('ResponseUnits')

        # Get temperature, air pressure, and humidity from the observation
        # data set.
        for i in range(len(descriptions)):
            d = descriptions[i].lower()

            if d in ['temp', 'temperature']:
                self._temperature = values[i]
                self._last_update = time.time()
                logger.debug('Updated temperature to {} °C'
                             .format(self._temperature))
                continue

            if d in ['airpressure', 'press', 'pressure']:
                self._pressure = values[i]
                self._last_update = time.time()
                logger.debug('Updated pressure to {} hPa'
                             .format(self._pressure))
                continue

            if d in ['humidity', 'moisture']:
                if units[i] == '%':
                    # Unit is percent (e.g., 75 %).
                    self._humidity = values[i] / 100
                else:
                    # No unit (e.g., 0.75).
                    self._humidity = values[i]

                self._last_update = time.time()
                logger.debug('Updated humidity to {}'
                             .format(round(self._humidity, 2)))
                continue

    def sealevel_reduction(self):
        pass

    def _get_ppm(self):
        """Calculates the atmospheric correction value in parts per million
        (ppm) for the reduction of distances gained by electronic distance
        measurement (EDM).

        The formulas are taken from the official manual of the Leica TM30
        robotic total station. They should be valid for all modern total
        stations of Leica Geosystems. For further information, please see Leica
        TM30 manual on page 76."""
        alpha = 1 / 273.15
        div = (1 + alpha * self._temperature)
        x = (7.5 * self._temperature / (237.3 + self._temperature)) + 0.7857

        s1 = 0.29525 * self._pressure
        s2 = 4.126 * math.pow(10, -4) * self._humidity

        ppm = 286.34 - ((s1 / div) - ((s2 / div) * math.pow(10, int(x))))

        return ppm

    def action(self, obs_data):
        sensor_type = obs_data.get('SensorType').lower()

        # Update atmospheric data if sensor is a meteorological station.
        if sensor_type in self._ws_types:
            self._update_meteorological_data(obs_data)

        # Check if atmospheric data has been set.
        if self._temperature == None or self._pressure == None or \
            self._humidity == None:
            logger.warning('No atmospheric data found')
            return obs_data

        # Check the age of the athmospheric data.
        max_age = 3600  # 1 hour

        if self._last_update - time.time() > max_age:
            logger.warning('Atmospheric data is older than {} hour(s)'
                           .format(int(max_age / 3600)))

        # Reduce the slope distance of the EDM measurement if the sensor is a
        # robotic total station.
        if sensor_type in self._ts_types:
            ppm = self._get_ppm()
            obs_data = self._reduce_distance(obs_data, ppm)

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
        self._config = self._config_manager.config[self._name]

        # Acronyms of the valid sensor types:
        #
        # RTS: Robotic Total Station
        # TPS: Tachymeter-Positionierungssystem
        # TST: Total Station Theodolite
        self._valid_types = ['rts', 'tachymeter', 'total station',
                             'totalstation', 'tps', 'tst']

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
            azimuth_angle = math.atan((azimuth_y - sensor_y) / \
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

    def action(self, obs_data):
        # Check the configuration for the given sensor port.
        port_name = obs_data.get('PortName')

        if self._config[port_name] == None:
            logger.error('No configuration found for port "{}"'.format(port_name))
            return obs_data

        sensor_type = obs_data.get('SensorType').lower()

        if not sensor_type in self._valid_types:
            logger.error('Sensor is not of type "total station"')
            return obs_data

        sensor_y = self._config[port_name]['SensorPosition']['East']
        sensor_x = self._config[port_name]['SensorPosition']['North']
        sensor_z = self._config[port_name]['SensorPosition']['Height']

        azimuth_y = self._config[port_name]['AzimuthPosition']['East']
        azimuth_x = self._config[port_name]['AzimuthPosition']['North']

        descriptions = obs_data.get('ResponseDescriptions')
        values = obs_data.get('ResponseValues')

        hz = None
        v = None
        dist = None

        # Get Hz, V, and distance from the observation data set.
        for i in range(len(descriptions)):
            d = descriptions[i].lower()

            if d == 'hz':
                hz = values[i]

            if d == 'v':
                v = values[i]

            if d in ['dist', 'slopedist']:
                dist = values[i]

        if hz == None or v == None or dist == None:
            logger.warning('Observation is incomplete '
                           '(Hz, V, or distance is missing)')

        hz_grad = hz * 200 / math.pi
        v_grad = v * 200 / math.pi

        logger.debug('Starting polar transformation of target "{}" with '
                     '[Hz = {:3.5f} gon, V = {:3.5f} gon, dist = {:4.5f} m]'
                     .format(obs_data.get('ID'),
                             hz_grad,
                             v_grad,
                             dist))

        (y, x, z) = self.transform(sensor_x, sensor_y, sensor_z,
                                   azimuth_x, azimuth_y, hz, v, dist)

        logger.debug('Transformed target "{}" to [Y = {:3.4f}, '
                     'X = {:3.4f}, Z = {:3.4f}]'.format(obs_data.get('ID'),
                                                        y,
                                                        x,
                                                        z))

        obs_data.data['ResponseDescriptions'].append('Y')
        obs_data.data['ResponseValues'].append(round(y, 5))
        obs_data.data['ResponseUnits'].append('m')

        obs_data.data['ResponseDescriptions'].append('X')
        obs_data.data['ResponseValues'].append(round(x, 5))
        obs_data.data['ResponseUnits'].append('m')

        obs_data.data['ResponseDescriptions'].append('Z')
        obs_data.data['ResponseValues'].append(round(z, 5))
        obs_data.data['ResponseUnits'].append('m')

        return obs_data

    def destroy(self, *args):
        pass

class PreProcessor(prototype.Prototype):

    """Extracts values from the raw responses of a given observation data set
    and converts them to the defined types.
    """

    def __init__(self, name, config_manager):
        prototype.Prototype.__init__(self, name, config_manager)

    def action(self, obs_data):
        """Extracts the values from the raw responses of the observation data
        using regular expressions. The result is forwarded by the message
        broker."""
        values = []

        response = obs_data.get('Response')
        response_pattern = obs_data.get('ResponsePattern')
        response_types = obs_data.get('ResponseTypes')

        pattern = re.compile(response_pattern)
        parsed = pattern.search(response)

        if not parsed:
            logger.warning('Extraction pattern "{}" does not match response '
                           '"{}" from sensor {} on {}'
                           .format(response_pattern,
                                   self._sanitize(response),
                                   obs_data.get('SensorName'),
                                   obs_data.get('PortName')))

        # The regular expression pattern needs a least one defined group
        # by using the braces "(" and ")". Otherwise, an extraction of the
        # values is not possible, which leads to an error.
        #
        # Right: "(.*)"
        # Wrong: ".*"
        groups = parsed.groups()

        if len(groups) == 0:
            logger.error('No group defined in regular expression pattern')
            return obs_data

        # The results go in here.
        values = []

        for i in range(len(groups)):
            g = groups[i]
            t = response_types[i].lower()

            logger.debug('Extracted "{}" from raw response'.format(g))

            # Convert raw value to float.
            if t == 'float':
                # Replace comma by dot.
                dotted = g.replace(',', '.')

                if self._is_float(dotted):
                    v = float(dotted)

                    logger.debug('Converted raw value "{}" to '
                                 'float value "{}"'.format(g, v))
                else:
                    logger.warning('Value {} couldn\'t be converted '
                                   '(not float)'.format(g))
            # Convert raw value to int.
            elif t == 'integer':
                if self._is_int(g):
                    v = int(g)

                    logger.debug('Converted raw value "{}" to '
                                 'integer value "{}"'.format(g, v))
                else:
                    logger.warning('Value {} couldn\'t be converted '
                                   '(not integer)'.format(g))
            # Convert raw value to string.
            else:
                # Well, in this case (input == output) do nothing.
                continue

            values.append(v)

        obs_data.set('ResponseValues', values)

        return obs_data

    def destroy(self, *args):
        pass

    def _is_int(self, value):
        """Returns whether a value is int or not."""
        try:
            int(value)
            return True
        except ValueError:
            return False

    def _is_float(self, value):
        """Returns whether a value is float or not."""
        try:
            float(value)
            return True
        except ValueError:
            return False

    def _sanitize(self, s):
        """Removes some non-printable characters from a string."""
        san = s.replace('\n', '\\n')
        san = san.replace('\r', '\\r')
        san = san.replace('\t', '\\t')

        return san
