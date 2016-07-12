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

from modules import prototype

logger = logging.getLogger('netadms')


class PolarTransformer(prototype.Prototype):

    """
    Calculates 3-dimensional coordinates of a target using the sensor position,
    and the azimuth position from the configuration together with the
    horizontal direction, the vertical angle, and the distance of a
    totalstation observation (TPS). The result (Y, X, Z) is added to the
    observation data set.
    """

    def __init__(self, name, config_manager):
        prototype.Prototype.__init__(self, name, config_manager)
        self._config = self._config_manager.config[self._name]

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

        # Acronyms of the valid sensor types:
        #
        # RTS: Robotic Total Station
        # TPS: Tachymeter Positionierungssystem
        # TST: Total Station Theodolite
        valid_types = ['rts', 'tachymeter', 'total station', 'totalstation',
                       'tps', 'tst']
        sensor_type = obs_data.get('SensorType').lower()

        if not sensor_type in valid_types:
            logger.error('Sensor is not of type "total station"')
            return obs_data

        sensor_y = self._config[port_name]['SensorPosition']['East']
        sensor_x = self._config[port_name]['SensorPosition']['North']
        sensor_z = self._config[port_name]['SensorPosition']['Height']

        azimuth_y = self._config[port_name]['AzimuthPosition']['East']
        azimuth_x = self._config[port_name]['AzimuthPosition']['North']

        for query in obs_data.get('Queries'):
            descriptions = query['ResponseDescriptions']
            values = query['ResponseValues']

            hz = None
            v = None
            dist = None

            # Get Hz, V, and distance from the observation data set.
            for i in range(len(descriptions)):
                d = descriptions[i].lower()

                if d == 'hz':
                    hz = values[i]
                    continue

                if d == 'v':
                    v = values[i]
                    continue

                if d in ['dist', 'slopedist']:
                    dist = values[i]
                    continue

            if hz == None or v == None or dist == None:
                logger.warning('Observation is incomplete '
                               '(Hz, V, or distance is missing)')
                continue

            hz_grad = hz * 200 / math.pi
            v_grad = v * 200 / math.pi

            logger.debug('Starting polar transformation of target "{}" with '
                         '[Hz = {:3.5f} gon, V = {:3.5f} gon, dist = {:4.5f} m]'
                         .format(query['ID'],
                                 hz_grad,
                                 v_grad,
                                 dist))

            (y, x, z) = self.transform(sensor_x, sensor_y, sensor_z,
                                       azimuth_x, azimuth_y, hz, v, dist)

            logger.debug('Transformed target "{}" to [Y = {:3.4f}, '
                         'X = {:3.4f}, Z = {:3.4f}]'.format(query['ID'],
                                                            y,
                                                            x,
                                                            z))

            query['ResponseDescriptions'].append('Y')
            query['ResponseValues'].append(round(y, 5))
            query['ResponseUnits'].append('m')

            query['ResponseDescriptions'].append('X')
            query['ResponseValues'].append(round(x, 5))
            query['ResponseUnits'].append('m')

            query['ResponseDescriptions'].append('Z')
            query['ResponseValues'].append(round(z, 5))
            query['ResponseUnits'].append('m')

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

        for query in obs_data.get('Queries'):
            response = query['Response']
            response_pattern = query['ResponsePattern']
            response_types = query['ResponseTypes']

            pattern = re.compile(response_pattern)
            parsed = pattern.search(response)

            if not parsed:
                logger.warning('Extraction pattern "{}" does not match '
                               'response "{}" from sensor {} on {}'
                               .format(response_pattern,
                                       self._sanitize(response),
                                       obs_data.get('SensorName'),
                                       obs_data.get('PortName')))
                continue

            # The regular expression pattern needs a least one defined group
            # by using the braces "(" and ")". Otherwise, an extraction of the
            # values is not possible and leads to an error.
            #
            # Right: "(.*)"
            # Wrong: ".*"
            groups = parsed.groups()

            if len(groups) == 0:
                logger.error('No group defined in the regular '
                             'expression pattern')
                return

            # The results go in here.
            values = []

            for i in range(len(groups)):
                g = groups[i]
                t = response_types[i]

                logger.debug('Extracted "{}" from raw response'.format(g))

                # Convert raw value to float.
                if t.lower() == 'float':
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
                elif t.lower() == 'integer':
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
                    break

                values.append(v)

            query['ResponseValues'] = values

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
