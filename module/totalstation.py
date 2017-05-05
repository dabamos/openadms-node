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

import math
import time

from core.observation import Observation
from core.sensor import SensorType
from module.prototype import Prototype

"""Module for the processing of observations of total station positioning
systems (pre-processing, atmospheric corrections, transformations)."""


class DistanceCorrector(Prototype):
    """
    Corrects the slope distance for EDM measurements using atmospheric
    data.
    """

    def __init__(self, name, type, manager):
        Prototype.__init__(self, name, type, manager)
        config = self._config_manager.get(self._name)

        # Maximum age of atmospheric data, before a warning will be generated.
        self._max_age = 3600
        # TODO ... maybe should be better part of the configuration?

        self._is_atmospheric_correction =\
            config.get('atmosphericCorrectionEnabled')
        self._is_sea_level_correction =\
            config.get('seaLevelCorrectionEnabled')

        self._distance_name = config.get('distanceName')
        self._temperature = config.get('temperature')
        self._pressure = config.get('pressure')
        self._humidity = config.get('humidity')
        self._sensor_height = config.get('sensorHeight')
        self._last_update = time.time()

    def process_observation(self, obs):
        sensor_type = obs.get('sensorType')

        # Update atmospheric data if sensor is a weather station.
        if SensorType.is_weather_station(sensor_type):
            self._update_meteorological_data(obs)
            return obs

        # Check if sensor is of type "total station".
        if not SensorType.is_total_station(sensor_type):
            self.logger.warning('Sensor type "{}" not supported'
                                .format(sensor_type))
            return obs

        # Check if atmospheric data has been set.
        if None in [self.temperature, self.pressure, not self.humidity]:
            self.logger.warning('No temperature, air pressure, or humidity set')
            return obs

        # Check the age of the atmospheric data.
        if self.last_update - time.time() > self._max_age:
            self.logger.warning('Atmospheric data is older than {} hour(s)'
                                .format(int(self._max_age / 3600)))

        # Reduce the slope distance of the EDM measurement.
        dist = obs.get_response_value(self._distance_name)

        if dist is None:
            return obs

        d_dist_1 = 0
        d_dist_2 = 0

        response_sets = obs.get('responseSets')

        # Calculate the atmospheric reduction of the distance.
        if self._is_atmospheric_correction:
            c = self.get_atmospheric_correction(self._temperature,
                                                self._pressure,
                                                self._humidity)
            d_dist_1 = dist * c * math.pow(10, -6)

            response_set = Observation.create_response_set('float',
                                                           'none',
                                                           round(c, 5))
            response_sets['atmosphericPpm'] = response_set

        # Calculate the sea level reduction of the distance.
        if self._is_sea_level_correction:
            d_dist_2 = self.get_sea_level_correction(self._sensor_height)

            response_set = Observation.create_response_set('float',
                                                           'm',
                                                           round(d_dist_2, 5))
            response_sets['seaLevelDelta'] = response_set

        # Add reduced distance to the observation set.
        if d_dist_1 != 0 or d_dist_2 != 0:
            r_dist = dist + d_dist_1 + d_dist_2

            self.logger.info('Reduced distance from {:0.5f} m to {:0.5f} m '
                             '(correction value: {:0.5f} m)'
                             .format(dist, r_dist, d_dist_1 + d_dist_2))

            response_set = Observation.create_response_set('float',
                                                           'm',
                                                           round(r_dist, 5))

            response_sets[self._distance_name + 'Raw'] =\
                response_sets.get(self._distance_name)
            response_sets[self._distance_name] = response_set

        return obs

    def get_atmospheric_correction(self, temperature, pressure, humidity):
        """Calculates the atmospheric correction value in parts per million
        (ppm) for the reduction of distances gained by electronic distance
        measurement (EDM).

        The formulas are taken from the official manual of the Leica TM30
        robotic total station. They should be valid for all modern total
        stations of Leica Geosystems. For further information, please see
        Leica TM30 manual on page 76."""
        alpha = 1 / 273.15
        div = 1 + (alpha * temperature)
        x = (7.5 * (temperature / (237.3 + temperature))) + 0.7857

        a = 0.29525 * pressure
        b = 4.126 * math.pow(10, -4) * humidity
        c = 286.34 - ((a / div) - ((b / div) * math.pow(10, x)))

        return c

    def get_sea_level_correction(self, sensor_height):
        earth_radius = 6.378 * math.pow(10, 6)
        c = -1 * (sensor_height / earth_radius)

        return c

    def _update_meteorological_data(self, obs):
        """Updates the temperature, air pressure, and humidity attributes by
        using the measured data of a weather station."""
        # Temperature.
        t = obs.get_response_value('temperature')

        if t is not None:
            self.temperature = t

        # Pressure.
        p = obs.get_response_value('pressure')

        if p is not None:
            self.pressure = p

        # Humidity.
        if obs.has_response_value('humidity') and\
            obs.has_response_type('humidity'):
            h = obs.get_response_value('humidity')
            u = obs.get_response_unit('humidity')

            self.humidity = h / 100 if u == '%' else h

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
            self.logger.info('Updated temperature to {} C'
                             .format(round(temperature, 2)))

    @pressure.setter
    def pressure(self, pressure):
        """Sets the air pressure."""
        self._pressure = pressure
        self._last_update = time.time()

        if pressure is not None:
            self.logger.info('Updated pressure to {} hPa'
                             .format(round(pressure, 2)))

    @humidity.setter
    def humidity(self, humidity):
        """Sets the humidity."""
        self._humidity = humidity
        self._last_update = time.time()

        if humidity is not None:
            self.logger.info('Updated humidity to {}'
                             .format(round(humidity, 2)))

    @last_update.setter
    def last_update(self, last_update):
        """Sets the timestamp of the last update."""
        self._last_update = last_update

    @sensor_height.setter
    def sensor_height(self, sensor_height):
        """Sets the height of the sensor."""
        self._sensor_height = sensor_height


class HelmertTransformer(Prototype):
    """
    HelmertTransformer calculates the 3-dimensional coordinates of a view point
    using the Helmert transformation.
    """

    def __init__(self, name, type, manager):
        Prototype.__init__(self, name, type, manager)
        config = self._config_manager.get(self._name)

        self._is_residual = config.get('residualMismatchTransformationEnabled')
        self._fixed_points = config.get('fixedPoints')
        self._view_point = config.get('viewPoint')

        # Initialize the view point.
        self._view_point['x'] = 0
        self._view_point['y'] = 0
        self._view_point['z'] = 0

        # Transformation parameters.
        self._a = None
        self._o = None

    def process_observation(self, obs):
        """Calculates the coordinates of the view point and further target
        points by using the Helmert transformation. The given observation can
        either be of a fixed point or of a target point.

        Measured polar coordinates of the fixed points are used to determine the
        Cartesian coordinates of the view point and the given target points.

        An `Observation` object will be created for the view point and send
        to the receivers defined in the configuration."""
        # Update the fixed point data of the configuration (Hz, V, slope distance)
        # by using the current observation.
        if self._is_fixed_point(obs):
            self._update_fixed_point(obs)

        # Only calculate the view point's coordinates if all fixed points have
        # been measured at least once.
        if self._is_ready():
            if self._is_fixed_point(obs):
                # Calculate the coordinates of the view point by using the
                # Helmert transformation and create a new observation of the
                # view point.
                view_point = self._calculate_view_point(obs)

                # Send the new view point observation to the next receiver.
                if view_point:
                    self.publish_observation(view_point)
            else:
                # Calculate the coordinates of the target point.
                obs = self._calculate_target_point(obs)

        return obs

    def calculate_point_coordinates(self,
                                    hz, v, dist,
                                    view_point_x, view_point_y, view_point_z,
                                    a, o):
        # Calculate Cartesian coordinates out of polar coordinates.
        local_x, local_y, local_z = self.get_cartesian_coordinates(hz,
                                                                   v,
                                                                   dist)

        x = view_point_x + (a * local_x) - (o * local_y)
        y = view_point_y + (a * local_y) + (o * local_x)
        z = view_point_z + local_z

        return x, y, z

    def _calculate_residual_mismatches(self, global_x, global_y):
        sum_p = 0
        sum_p_vx = 0
        sum_p_vy = 0

        # Calculate residual mismatches.
        for fixed_point_id, fixed_point in self._fixed_points.items():
            a = math.pow(global_x - fixed_point.get('x'), 2)
            b = math.pow(global_y - fixed_point.get('y'), 2)
            s = math.sqrt(a + b)
            p = 1 / s

            # Global Cartesian coordinates of the fixed point.
            x, y, z = self.calculate_point_coordinates(
                fixed_point.get('hz'),
                fixed_point.get('v'),
                fixed_point.get('dist'),
                self._view_point.get('x'),
                self._view_point.get('y'),
                self._view_point.get('z'),
                self._a,
                self._o)

            vx = fixed_point.get('x') - x
            vy = fixed_point.get('y') - y

            sum_p_vx += p * vx
            sum_p_vy += p * vy
            sum_p += p

        vx = sum_p_vx / sum_p
        vy = sum_p_vy / sum_p

        return vx, vy

    def _calculate_target_point(self, obs):
        hz = obs.get_response_value('hz')
        v = obs.get_response_value('v')
        dist = obs.get_response_value('slopeDist')

        if None in [hz, v, dist]:
            self.logger.warning('Hz, V, or distance is missing in observation '
                                '"{}" with ID "{}"'.format(obs.get('name'),
                                                           obs.get('id')))
            return obs

        # Calculate the coordinates in the global system (X, Y, Z).
        x, y, z = self.calculate_point_coordinates(
            hz,
            v,
            dist,
            self._view_point.get('x'),
            self._view_point.get('y'),
            self._view_point.get('z'),
            self._a,
            self._o)

        self.logger.info('Calculated coordinates of target point "{}" '
                         '(X = {:4.5f}, Y = {:4.5f}, Z = {:4.5g})'
                         .format(obs.get('id'), x, y, z))

        # Do residual mismatch transformation.
        if self._is_residual:
            vx, vy = self._calculate_residual_mismatches(x, y)

            self.logger.debug('Calculated improvements for target point "{}" '
                              '(dX = {:4.5f} m, dY = {:4.5f} m)'
                              .format(obs.get('id'), vx, vy))

            x += vx
            y += vy

            self.logger.debug('Updated coordinates of target point "{}" '
                              '(X = {:4.5f}, Y = {:4.5f})'
                              .format(obs.get('id'), x, y))

        # Add response set.
        response_sets = obs.get('responseSets')
        response_sets['x'] = Observation.create_response_set('float', 'm', x)
        response_sets['y'] = Observation.create_response_set('float', 'm', y)
        response_sets['z'] = Observation.create_response_set('float', 'm', z)

        return obs

    def _calculate_view_point(self, obs):
        sum_local_x = sum_local_y = sum_local_z = 0     # [x], [y], [z].
        sum_global_x = sum_global_y = sum_global_z = 0  # [X], [Y], [Z].
        num_fixed_points = len(self._fixed_points)      # n.

        # Calculate the centroid coordinates of the view point.
        for name, fixed_point in self._fixed_points.items():
            hz = fixed_point.get('hz')        # Horizontal direction.
            v = fixed_point.get('v')          # Vertical angle.
            dist = fixed_point.get('dist')    # Distance (slope or reduced).

            if None in [hz, v, dist]:
                self.logger.warning('Hz, V, or distance is missing in '
                                    'observation "{}" with ID "{}"'
                                    .format(obs.get('name'), obs.get('id')))
                return

            # Calculate Cartesian coordinates out of polar coordinates.
            local_x, local_y, local_z = self.get_cartesian_coordinates(hz,
                                                                       v,
                                                                       dist)

            # Store local coordinates in the fixed point dictionary.
            fixed_point['localX'] = local_x
            fixed_point['localY'] = local_y
            fixed_point['localZ'] = local_z

            # Coordinates in the global system (X, Y, Z).
            global_x = fixed_point.get('x')
            global_y = fixed_point.get('y')
            global_z = fixed_point.get('z')

            if None in [global_x, global_y, global_z]:
                self.logger.error('Fixed point "{}" not set in configuration'
                                  .format(name))

            # Sums of the coordinates.
            sum_local_x += local_x
            sum_local_y += local_y
            sum_local_z += local_z

            sum_global_x += global_x
            sum_global_y += global_y
            sum_global_z += global_z

        # Coordinates of the centroids.
        local_centroid_x = sum_local_x / num_fixed_points     # x_s.
        local_centroid_y = sum_local_y / num_fixed_points     # y_s.

        global_centroid_x = sum_global_x / num_fixed_points   # X_s.
        global_centroid_y = sum_global_y / num_fixed_points   # Y_s.

        # Calculate transformation parameters.
        o_1 = o_2 = 0
        a_1 = a_2 = 0

        for name, fixed_point in self._fixed_points.items():
            local_x = fixed_point.get('localX')
            local_y = fixed_point.get('localY')

            global_x = fixed_point.get('x')
            global_y = fixed_point.get('y')

            # Reduced coordinates of the centroids.
            r_local_centroid_x = local_x - local_centroid_x
            r_local_centroid_y = local_y - local_centroid_y

            r_global_centroid_x = global_x - global_centroid_x
            r_global_centroid_y = global_y - global_centroid_y

            # o = [ x_i * Y_i - y_i * X_i ] * [ x_i^2 + y_i^2 ]^-1
            o_1 += (r_local_centroid_x * r_global_centroid_y) -\
                   (r_local_centroid_y * r_global_centroid_x)
            o_2 += math.pow(r_local_centroid_x, 2) +\
                   math.pow(r_local_centroid_y, 2)

            # a = [ x_i * X_i + y_i * Y_i ] * [ x_i^2 + y_i^2 ]^-1
            a_1 += (r_local_centroid_x * r_global_centroid_x) +\
                   (r_local_centroid_y * r_global_centroid_y)
            a_2 += math.pow(r_local_centroid_x, 2) +\
                   math.pow(r_local_centroid_y, 2)

        self._o = o_1 / o_2 if o_2 != 0 else 0   # Parameter o.
        self._a = a_1 / a_2 if a_2 != 0 else 0   # Parameter a.

        # Calculate the coordinates of the view point:
        # Y_0 = Y_s - a * y_s - o * x_s
        # X_0 = X_s - a * x_s + o * y_s
        # Z_0 = ([Z] - [z]) / n
        self._view_point['x'] = global_centroid_x -\
                                (self._a * local_centroid_x) +\
                                (self._o * local_centroid_y)
        self._view_point['y'] = global_centroid_y -\
                                (self._a * local_centroid_y) -\
                                (self._o * local_centroid_x)
        self._view_point['z'] = (sum_global_z - sum_local_z) / num_fixed_points

        self.logger.info('Calculated coordinates of view point "{}" '
                         '(X = {:4.5f}, Y = {:4.5f}, Z = {:4.5f})'
                         .format(self._view_point.get('id'),
                                 self._view_point.get('x'),
                                 self._view_point.get('y'),
                                 self._view_point.get('z')))

        # Calculate the standard deviations.
        sum_wx = sum_wy = 0                     # [W_x], [W_y].
        sum_wx_wx = sum_wy_wy = sum_wz_wz = 0   # [W_x^2], [W_y^2], [W_z^2].

        for name, fixed_point in self._fixed_points.items():
            local_x = fixed_point.get('localX')
            local_y = fixed_point.get('localY')
            local_z = fixed_point.get('localZ')

            global_x = fixed_point.get('x')
            global_y = fixed_point.get('y')
            global_z = fixed_point.get('z')

            view_point_x = self._view_point.get('x')
            view_point_y = self._view_point.get('y')
            view_point_z = self._view_point.get('z')

            wx_i = (-1 * view_point_x) - (self._a * local_x) +\
                   (self._o * local_y) + global_x
            wy_i = (-1 * view_point_y) - (self._a * local_y) -\
                   (self._o * local_x) + global_y

            sum_wx += wx_i
            sum_wy += wy_i

            sum_wx_wx += wx_i * wx_i
            sum_wy_wy += wy_i * wy_i
            sum_wz_wz += math.pow(view_point_z - (global_z - local_z), 2)

        # Sum of discrepancies should be 0, i.e. [W_x] = [W_y] = 0.
        r_sum_wx = abs(round(sum_wx, 5))
        r_sum_wy = abs(round(sum_wy, 5))

        if r_sum_wx != 0 or r_sum_wy != 0:
            self.logger.warning('Calculated coordinates of view point "{}" '
                                'are inaccurate ([Wx] = {}, [Wy] = {})'
                                .format(self._view_point.get('id'),
                                        r_sum_wx,
                                        r_sum_wy))

        # Standard deviations.
        sx = math.sqrt((sum_wx_wx + sum_wy_wy) / ((2 * num_fixed_points) - 4))
        sy = sx
        sz = math.sqrt(sum_wz_wz / (num_fixed_points - 1))

        self.logger.debug('Calculated standard deviations '
                          '(sX = {:1.5f} m, sY = {:1.5f} m, sZ = {:1.5f} m)'
                          .format(sx, sy, sz))

        # Scale factor.
        m = math.sqrt((self._a * self._a) + (self._o * self._o))
        self.logger.debug('Calculated scale factor (m = {})'
                          .format(round(m, 5)))

        # Create response sets for the view point.
        response_sets = {
            'x': Observation.create_response_set('float', 'm',
                                                 self._view_point['x']),
            'y': Observation.create_response_set('float', 'm',
                                                 self._view_point['y']),
            'z': Observation.create_response_set('float', 'm',
                                                 self._view_point['z']),
            'stdDevX': Observation.create_response_set('float', 'm', sx),
            'stdDevY': Observation.create_response_set('float', 'm', sy),
            'stdDevZ': Observation.create_response_set('float', 'm', sz),
            'scaleFactor': Observation.create_response_set('float', 'm', m)
        }

        # Create Observation instance for the view point.
        view_point = Observation()
        view_point.set('id', self._view_point.get('id'))
        view_point.set('name', 'getViewPoint')
        view_point.set('nextReceiver', 0)
        view_point.set('portName', obs.get('portName'))
        view_point.set('receivers', self._view_point.get('receivers'))
        view_point.set('responseSets', response_sets)
        view_point.set('timeStamp', time.time())

        # Return the Observation object of the view point.
        return view_point

    def get_cartesian_coordinates(self, hz, v, slope_dist):
        hz_dist = slope_dist * math.sin(v)

        x = hz_dist * math.cos(hz)
        y = hz_dist * math.sin(hz)
        z = slope_dist * math.cos(v)

        return x, y, z

    def _is_fixed_point(self, obs):
        """Checks if the given observation equals one of the defined fixed
        points."""
        if self._fixed_points.get(obs.get('id')):
            return True
        else:
            return False

    def _is_ready(self):
        """Checks whether all fixed points have been measured at least once."""
        for fixed_point_id, fixed_point in self._fixed_points.items():
            if fixed_point.get('lastUpdate') is None:
                # Tie point has not been measured yet.
                return False

        return True

    def _update_fixed_point(self, obs):
        """Adds horizontal direction, vertical angle, and slope distance
        of the observation to a fixed point."""
        hz = obs.get_response_value('hz')
        v = obs.get_response_value('v')
        dist = obs.get_response_value('slopeDist')

        if None in [hz, v, dist]:
            return obs

        # Calculate the coordinates of the fixed point if the Helmert
        # transformation has been done already. Otherwise, use the datum from
        # the configuration.
        fixed_point = self._fixed_points.get(obs.get('id'))

        if self._is_ready():
            x, y, z = self.calculate_point_coordinates(
                hz,
                v,
                dist,
                self._view_point.get('x'),
                self._view_point.get('y'),
                self._view_point.get('z'),
                self._a,
                self._o)

            self.logger.info('Calculated coordinates of fixed point "{}" '
                             '(X = {:3.5f}, Y = {:3.5f}, Z = {:3.5f})'
                             .format(obs.get('id'), x, y, z))
        else:
            # Get the coordinates of the fixed point from the configuration.
            x = fixed_point.get('x')
            y = fixed_point.get('y')
            z = fixed_point.get('z')

        # Update the values.
        fixed_point['hz'] = hz
        fixed_point['v'] = v
        fixed_point['dist'] = dist
        fixed_point['lastUpdate'] = time.time()

        self.logger.debug('Updated fixed point with ID "{}"'
                          .format(obs.get('id')))

        # Add global Cartesian coordinates of the fixed point to the
        # observation.
        response_sets = obs.get('responseSets')
        response_sets['x'] = Observation.create_response_set('float', 'm', x)
        response_sets['y'] = Observation.create_response_set('float', 'm', y)
        response_sets['z'] = Observation.create_response_set('float', 'm', z)


class PolarTransformer(Prototype):
    """
    PolarTransformer calculates 3-dimensional coordinates of a target using the
    sensor position and the azimuth position from the configuration together
    with the horizontal direction, the vertical angle, and the distance of a
    total station observation. The result (Y, X, Z) is added to the observation
    data set.

    It is possible to use multiple fixed points in order to improve the
    accuracy of the horizontal directions ('Abriss' in German).
    """

    def __init__(self, name, type, manager):
        Prototype.__init__(self, name, type, manager)
        config = self._config_manager.get(self._name)

        self._view_point = config.get('viewPoint')
        self._fixed_points = config.get('fixedPoints')

        self._azimuth_point_name = config.get('azimuthPointName')
        self._azimuth_point = self._fixed_points.get(self._azimuth_point_name)

        if not self._azimuth_point:
            self.logger.error('Azimuth point "{}" doesn\'t exist'
                              .format(self._azimuth_point_name))

        self._azimuth_angle = self.gon_to_rad(config.get('azimuthAngle'))
        self._is_adjustment_enabled = config.get('adjustmentEnabled')

    def _get_adjustment_value(self):
        delta_hz_sum = 0
        fixed_point_count = 0
        r = 0

        for fixed_point_id, fixed_point in self._fixed_points.items():
            if fixed_point.get('deltaHz') is None:
                # Fixed point has not been measured yet.
                continue

            delta_hz_sum += fixed_point.get('deltaHz')
            fixed_point_count += 1

        if fixed_point_count > 0:
            r = delta_hz_sum / fixed_point_count

        return r

    def _is_fixed_point(self, obs):
        """Checks if the given observation equals one of the defined fixed
        points."""
        if self._fixed_points.get(obs.get('id')):
            return True
        else:
            return False

    def _is_valid_sensor_type(self, obs):
        sensor_type = obs.get('sensorType')

        if not SensorType.is_total_station(sensor_type.lower()):
            self.logger.error('Sensor type "{}" is not supported'
                              .format(sensor_type))
            return False

        return True

    def _update_fixed_point(self, obs):
        fixed_point = self._fixed_points.get(obs.get('id'))
        hz = obs.get_response_value('hz')

        azimuth = self.get_azimuth_angle(self._azimuth_angle,
                                         self._view_point.get('x'),
                                         self._view_point.get('y'),
                                         fixed_point.get('x'),
                                         fixed_point.get('y'))

        fixed_point['hz'] = hz
        fixed_point['azimuth'] = azimuth
        fixed_point['lastUpdate'] = time.time()

        # Calculate the orientation.
        delta_hz = azimuth - hz

        if delta_hz < 0:
            # Add 400 gon.
            delta_hz += 2 * math.pi

        fixed_point['deltaHz'] = delta_hz

    def get_azimuth_angle(self,
                          view_point_azimuth,
                          view_point_x, view_point_y,
                          target_point_x, target_point_y):
        """Calculates the azimuth angle to a target point by using the
        direction and the distance from a view point."""
        # Angle to the target point.
        azimuth = 0.0

        # Calculate azimuth angle out of coordinates.
        d_x = target_point_x - view_point_x
        d_y = target_point_y - view_point_y

        if d_x == 0:
            if d_y > 0:
                azimuth = 0.5 * math.pi
            elif d_y < 0:
                azimuth = 1.5 * math.pi
            elif d_y == 0:
                self.logger.error('Sensor position equals azimuth position')
        else:
            azimuth = math.atan(d_y / d_x)

        # Consider the quadrant of the target point.
        if d_x < 0:
            # Add 200 gon.
            azimuth += math.pi

        if d_y < 0 < d_x:
            # Add 400 gon.
            azimuth += 2 * math.pi

        # Remove the global azimuth angle of the sensor from the calculated
        # local azimuth.
        if azimuth != 0:
            azimuth = azimuth - view_point_azimuth

        return azimuth

    def process_observation(self, obs):
        if not self._is_valid_sensor_type(obs):
            # Only total stations are supported.
            return obs

        hz = obs.get_response_value('hz')
        v = obs.get_response_value('v')
        dist = obs.get_response_value('slopeDist')

        if None in [hz, v, dist]:
            return obs

        # Calculate the horizontal distance.
        dist_hz = math.sin(v) * dist

        if self._is_fixed_point(obs):
            # Add measured Hz and calculated Hz to the fixed point.
            self._update_fixed_point(obs)
            self.logger.debug('Updated fixed point with ID "{}"'
                              .format(obs.get('id')))

        self.logger.debug('Starting polar transformation of target "{}" (Hz = '
                          '{:3.5f} gon, V = {:3.5f} gon, dist = {:4.5f} m)'
                          .format(obs.get('id'),
                                  self.rad_to_gon(hz),
                                  self.rad_to_gon(v),
                                  dist_hz))

        if self._is_adjustment_enabled:
            # Add the adjustment value to the horizontal direction.
            adj = self._get_adjustment_value()
            self.logger.info('Calculated adjustment value for polar '
                             'transformation ({:3.5f} gon)'
                             .format(self.rad_to_gon(adj)))
            hz += adj

        # Calculate the coordinates of the observation.
        x, y, z = self.transform(self._view_point.get('x'),
                                 self._view_point.get('y'),
                                 self._view_point.get('z'),
                                 self._azimuth_point.get('x'),
                                 self._azimuth_point.get('y'),
                                 hz,
                                 v,
                                 dist_hz)

        self.logger.info('Transformed target "{}" (X = {:3.4f}, Y = {:3.4f}, '
                         'Z = {:3.4f})'.format(obs.get('id'), x, y, z))

        # Add to observation data set.
        response_sets = obs.get('responseSets')
        response_sets['x'] = Observation.create_response_set('float',
                                                             'm',
                                                             round(x, 5))
        response_sets['y'] = Observation.create_response_set('float',
                                                             'm',
                                                             round(y, 5))
        response_sets['z'] = Observation.create_response_set('float',
                                                             'm',
                                                             round(z, 5))

        if self._is_adjustment_enabled:
            response_sets['hzAdjusted'] = Observation.create_response_set(
                'float',
                'rad',
                round(hz, 16)
            )

        return obs

    def transform(self,
                  view_point_x, view_point_y, view_point_z,
                  target_point_x, target_point_y,
                  hz, v, dist):
        """Calculates coordinates (x, y, z) out of horizontal direction,
        vertical angle, and slope distance to a target point using a
        3-dimensional polar transformation."""
        t = self.get_azimuth_angle(0,
                                   view_point_x,
                                   view_point_y,
                                   target_point_x,
                                   target_point_y)

        # Append the measured horizontal direction to the angle.
        t += hz

        # Calculate coordinates of the target point.
        d_x = dist * math.sin(v) * math.cos(t)
        d_y = dist * math.sin(v) * math.sin(t)
        d_z = dist * math.cos(v)

        x = view_point_x + d_x
        y = view_point_y + d_y
        z = view_point_z + d_z

        return x, y, z

    def gon_to_rad(self, a):
        """Converts from gon (grad) to radiant."""
        return a * math.pi / 200

    def rad_to_gon(self, a):
        """Converts from radiant to gon (grad)."""
        return a * 200 / math.pi


class RefractionCorrector(Prototype):
    """
    RefractionCorrector removes the influence of the refraction from a measured
    distance and corrects the Z value of an observed target.
    """

    def __init__(self, name, type, manager):
        Prototype.__init__(self, name, type, manager)

    def process_observation(self, obs):
        z = obs.get_response_value('z')

        if not z:
            return obs

        d = obs.get_response_value('slopeDist')

        if not d:
            return obs

        k = 0.13                    # Refraction coefficient.
        r = 6370000                 # Earth radius.

        k_e = (d * d) / (2 * r)     # Correction of earth radius.
        k_r = k * k_e               # Correction of refraction.
        r = k_e - k_r

        self.logger.info('Updated height of observation "{}" with ID "{}" '
                         'from {:3.4f} m to {:3.4f} m (refraction value: '
                         '{:3.5f} m)'.format(obs.get('name'),
                                             obs.get('id'),
                                             z,
                                             z + r,
                                             r))

        refraction = Observation.create_response_set('float', 'm', round(r, 6))
        z_new = Observation.create_response_set('float', 'm', round(z + r, 5))
        z_raw = Observation.create_response_set('float', 'm', z)

        obs.data['responseSets']['refraction'] = refraction
        obs.data['responseSets']['zRaw'] = z_raw
        obs.data['responseSets']['z'] = z_new

        return obs


class SerialMeasurementProcessor(Prototype):
    """
    SerialMeasurementProcessor calculates serial measurements by using
    observations of one target in two faces. The two faces, consisting of
    horizontal directions, vertical angles, and slope distances, are
    averaged and stored in a new response set.
    """

    def __init__(self, name, type, manager):
        Prototype.__init__(self, name, type, manager)

    def process_observation(self, obs):
        # Calculate the serial measurement of an observation in two faces.
        hz_0 = obs.get_response_value('hz0')
        hz_1 = obs.get_response_value('hz1')

        v_0 = obs.get_response_value('v0')
        v_1 = obs.get_response_value('v1')

        dist_0 = obs.get_response_value('slopeDist0')
        dist_1 = obs.get_response_value('slopeDist1')

        if None in [hz_0, hz_1, v_0, v_1, dist_0, dist_1]:
            return obs

        # Calculate new Hz, V, and slope distance.
        hz = hz_0 + hz_1

        if hz_0 > hz_1:
            hz += math.pi
        else:
            hz -= math.pi

        hz /= 2

        v = ((2 * math.pi) + (v_0 - v_1)) / 2
        dist = (dist_0 + dist_1) / 2

        # Save the calculated values.
        response_sets = obs.get('responseSets')
        response_sets['hz'] = Observation.create_response_set('float',
                                                              'rad',
                                                              hz)
        response_sets['v'] = Observation.create_response_set('float',
                                                             'rad',
                                                              v)
        response_sets['slopeDist'] = Observation.create_response_set('float',
                                                                     'm',
                                                                     dist)

        self.logger.debug('Calculated serial measurement with two faces for '
                          'observation "{}" with ID "{}"'
                          .format(obs.get('name'), obs.get('id')))

        return obs
