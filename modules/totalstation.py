#!/usr/bin/envython3
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

import math
import time

from core.observation import Observation
from core.sensor import SensorType
from modules.prototype import Prototype

"""Module for data processing (pre-processing, atmospheric corrections,
transformations)."""


class DistanceCorrector(Prototype):
    """
    Corrects the slope distance for EDM measurements using atmospheric
    data.
    """

    def __init__(self, name, config_manager, sensor_manager):
        Prototype.__init__(self, name, config_manager, sensor_manager)
        config = self._config_manager.config.get(self._name)

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
        if not self.temperature or not self.pressure or not self.humidity:
            self.logger.warning(
                'No temperature, air pressure, or humidity set')
            return obs

        # Check the age of the atmospheric data.
        if self.last_update - time.time() > self._max_age:
            self.logger.warning('Atmospheric data is older than {} hour(s)'
                                .format(int(self._max_age / 3600)))

        # Reduce the slope distance of the EDM measurement if the sensor is a
        # robotic total station.
        dist = obs.get_value('responseSets', self._distance_name, 'value')

        if dist is None:
            self.logger.warning('No distance set in observation "{}" with ID '
                                '"{}"'.format(obs.get('name'), obs.get('id')))
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

            response_set = self.get_response_set('float',
                                                 'none',
                                                 round(c, 5))
            response_sets['atmosphericPpm'] = response_set

        # Calculate the sea level reduction of the distance.
        if self._is_sea_level_correction:
            d_dist_2 = self.get_sea_level_correction(self._sensor_height)

            response_set = self.get_response_set('float',
                                                 'm',
                                                 round(d_dist_2, 5))
            response_sets['seaLevelDelta'] = response_set

        # Add reduced distance to the observation set.
        if d_dist_1 != 0 or d_dist_2 != 0:
            r_dist = dist + d_dist_1 + d_dist_2

            self.logger.info('Reduced distance from {:0.5f} m to {:0.5f} m '
                             '(correction value: {:0.5f} m)'
                             .format(dist, r_dist, d_dist_1 + d_dist_2))

            response_set = self.get_response_set('float',
                                                 'm',
                                                 round(r_dist, 5))

            response_sets[self._distance_name + 'Raw'] =\
                response_sets.get(self._distance_name)
            response_sets[self._distance_name] = response_set

        return obs

    @staticmethod
    def get_atmospheric_correction(temperature, pressure, humidity):
        """Calculates the atmospheric correction value in parts per million
        (ppm) for the reduction of distances gained by electronic distance
        measurement (EDM).

        The formulas are taken from the official manual of the Leica TM30
        robotic total station. They should be valid for all modern total
        stations of Leica Geosystems. For further information, please see Leica
        TM30 manual on page 76."""
        alpha = 1 / 273.15
        div = 1 + (alpha * temperature)
        x = (7.5 * (temperature / (237.3 + temperature))) + 0.7857

        a = 0.29525 * pressure
        b = 4.126 * math.pow(10, -4) * humidity
        c = 286.34 - ((a / div) - ((b / div) * math.pow(10, x)))

        return c

    @staticmethod
    def get_sea_level_correction(sensor_height):
        earth_radius = 6.378 * math.pow(10, 6)
        c = -1 * (sensor_height / earth_radius)

        return c

    def _update_meteorological_data(self, obs):
        """Updates the temperature, air pressure, and humidity attributes by
        using the measured data of a weather station."""
        try:
            t = obs.get('responseSets').get('temperature').get('value')

            if t is not None:
                self.temperature = t
            else:
                self.logger.warning('No temperature set in observation "{}" '
                                    'with ID "{}"'.format(obs.get('name'),
                                                          obs.get('id')))
        except AttributeError:
            # No temperature value found.
            pass

        try:
            p = obs.get('responseSets').get('pressure').get('value')

            if p is not None:
                self.pressure = p
            else:
                self.logger.warning('No pressure set in observation "{}" with '
                                    'ID "{}"'.format(obs.get('name'),
                                                     obs.get('id')))
        except AttributeError:
            # No pressure value found.
            pass

        try:
            h = obs.get('responseSets').get('humidity').get('value')
            u = obs.get('responseSets').get('humidity').get('unit')

            if h is not None and u is not None:
                self.humidity = h / 100 if u == '%' else h
            else:
                self.logger.warning('No humidity set in observation "{}" with '
                                    'ID "{}"'.format(obs.get('name'),
                                                     obs.get('id')))
        except AttributeError:
            # No humidity value found.
            pass

    def get_response_set(self, t, u, v):
        return {'type': t, 'unit': u, 'value': v}

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
    HelmertTransformer calculates a 3-dimensional coordinates of a view point
    using the Helmert transformation.
    """

    def __init__(self, name, config_manager, sensor_manager):
        Prototype.__init__(self, name, config_manager, sensor_manager)
        config = self._config_manager.config.get(self._name)

        self._is_residual = config.get('ResidualMismatchTransformationEnabled')
        self._tie_points = config.get('tiePoints')
        self._view_point = config.get('viewPoint')

        # Initialize the view point.
        self._view_point['x'] = 0
        self._view_point['y'] = 0
        self._view_point['z'] = 0

        self._a = None
        self._o = None

    def process_observation(self, obs):
        """Calculates the coordinates of the view point and further target
        points by using the Helmert transformation. The given observation can
        either be of a tie point or of a target point.

        Measured polar coordinates of the tie points are used to determine the
        Cartesian coordinates of the view point and given target points.

        An `Observation` object will be created for the view point and send
        to the receivers defined in the configuration."""
        # Update the tie point data (Hz, V, slope distance).
        if self._is_tie_point(obs):
            self._update_tie_point(obs)

        # Only calculate the view point's coordinates if all tie points have
        # been measured at least once.
        if self._is_ready():
            if self._is_tie_point(obs):
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

    @staticmethod
    def _calculate_point_coordinates(hz, v, dist,
                                     view_point_x, view_point_y, view_point_z,
                                     a, o):
        # Calculate Cartesian coordinates out of polar coordinates.
        local_x, local_y, local_z = _get_cartesian_coordinates(hz, v, dist)

        x = view_point_x + (a * local_x) - (o * local_y)
        y = view_point_y + (a * local_y) + (o * local_x)
        z = view_point_z + local_z

        return x, y, z

    def _calculate_residual_mismatches(self, global_x, global_y):
        sum_p = 0
        sum_p_vx = 0
        sum_p_vy = 0

        # Calculate residual mismatches.
        for tie_point_id, tie_point in self._tie_points.items():
            a = math.pow(global_x - tie_point.get('x'), 2)
            b = math.pow(global_y - tie_point.get('y'), 2)
            s = math.sqrt(a + b)
            p = 1 / s

            # Global Cartesian coordinates of the tie point.
            x, y, z = self._calculate_point_coordinates(
                tie_point.get('hz'),
                tie_point.get('v'),
                tie_point.get('dist'),
                self._view_point.get('x'),
                self._view_point.get('y'),
                self._view_point.get('z'),
                self._a,
                self._o)

            vx = tie_point.get('x') - x
            vy = tie_point.get('y') - y

            sum_p_vx += p * vx
            sum_p_vy += p * vy
            sum_p += p

        vx = sum_p_vx / sum_p
        vy = sum_p_vy / sum_p

        return vx, vy

    def _calculate_target_point(self, obs):
        hz = obs.get_value('responseSets', 'hz', 'value')
        v = obs.get_value('responseSets', 'v', 'value')
        dist = obs.get_value('responseSets', 'slopeDist', 'value')

        if None in [hz, v, dist]:
            self.logger.warning('Hz, V, or distance is missing in observation '
                                '"{}" with ID "{}"'.format(obs.get('name'),
                                                           obs.get('id')))
            return obs

        # Calculate the coordinates in the global system (X, Y, Z).
        x, y, z = self._calculate_point_coordinates(
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

            self.logger.debug(
                'Updated coordinates of target point "{}" '
                '(X = {:4.5f}, Y = {:4.5f})'.format(
                    obs.get('id'), x, y))

        # Add response set.
        response_sets = obs.get('responseSets')
        response_sets['x'] = self.get_response_set('float', 'm', x)
        response_sets['y'] = self.get_response_set('float', 'm', y)
        response_sets['z'] = self.get_response_set('float', 'm', z)

        return obs

    def _calculate_view_point(self, obs):
        sum_local_x = sum_local_y = sum_local_z = 0     # [x], [y], [z].
        sum_global_x = sum_global_y = sum_global_z = 0  # [X], [Y], [Z].
        num_tie_points = len(self._tie_points)          # n.

        # Calculate the centroid coordinates of the view point.
        for name, tie_point in self._tie_points.items():
            hz = tie_point.get('hz')        # Horizontal direction.
            v = tie_point.get('v')          # Vertical angle.
            dist = tie_point.get('dist')    # Distance (slope or reduced).

            if None in [hz, v, dist]:
                self.logger.warning('Hz, V, or distance is missing in '
                                    'observation "{}" with ID "{}"'
                                    .format(obs.get('name'), obs.get('id')))
                return

            # Calculate Cartesian coordinates out of polar coordinates.
            local_x, local_y, local_z = _get_cartesian_coordinates(hz, v, dist)

            # Store local coordinates in the tie point dictionary.
            tie_point['localX'] = local_x
            tie_point['localY'] = local_y
            tie_point['localZ'] = local_z

            # Coordinates in the global system (X, Y, Z).
            global_x = tie_point.get('x')
            global_y = tie_point.get('y')
            global_z = tie_point.get('z')

            if global_x is None or global_y is None or global_z is None:
                self.logger.error('Tie point "{}" not set in configuration'
                                  .format(name))

            # Sums of the coordinates.
            sum_local_x += local_x
            sum_local_y += local_y
            sum_local_z += local_z

            sum_global_x += global_x
            sum_global_y += global_y
            sum_global_z += global_z

        # Coordinates of the centroids.
        local_centroid_x = sum_local_x / num_tie_points     # x_s.
        local_centroid_y = sum_local_y / num_tie_points     # y_s.

        global_centroid_x = sum_global_x / num_tie_points   # X_s.
        global_centroid_y = sum_global_y / num_tie_points   # Y_s.

        # Calculate transformation parameters.
        o_1 = o_2 = 0
        a_1 = a_2 = 0

        for name, tie_point in self._tie_points.items():
            local_x = tie_point.get('localX')
            local_y = tie_point.get('localY')

            global_x = tie_point.get('x')
            global_y = tie_point.get('y')

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

        self._o = o_1 / o_2  # Parameter o.
        self._a = a_1 / a_2  # Parameter a.

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
        self._view_point['z'] = (sum_global_z - sum_local_z) / num_tie_points

        self.logger.info('Calculated coordinates of view point "{}" '
                         '(X = {:4.5f}, Y = {:4.5f}, Z = {:4.5f})'
                         .format(self._view_point.get('id'),
                                 self._view_point.get('x'),
                                 self._view_point.get('y'),
                                 self._view_point.get('z')))

        # Calculate the standard deviations.
        sum_wx = sum_wy = 0  # [W_x], [W_y].
        sum_wx_wx = sum_wy_wy = sum_wz_wz = 0  # [W_x^2], [W_y^2], [W_z^2].

        for name, tie_point in self._tie_points.items():
            local_x = tie_point.get('localX')
            local_y = tie_point.get('localY')
            local_z = tie_point.get('localZ')

            global_x = tie_point.get('x')
            global_y = tie_point.get('y')
            global_z = tie_point.get('z')

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
            self.logger.warning(
                'Calculated coordinates of view point "{}" are '
                'inaccurate ([Wx] = {}, [Wy] = {})' .format(
                    self._view_point.get('id'), r_sum_wx, r_sum_wy))

        # Standard deviations.
        sx = math.sqrt((sum_wx_wx + sum_wy_wy) / ((2 * num_tie_points) - 4))
        sy = sx
        sz = math.sqrt(sum_wz_wz / (num_tie_points - 1))

        self.logger.debug('Calculated standard deviations '
                          '(sX = {:1.5f} m, sY = {:1.5f} m, sZ = {:1.5f} m)'
                          .format(sx, sy, sz))

        # Scale factor.
        m = math.sqrt((self._a * self._a) + (self._o * self._o))
        self.logger.debug('Calculated scale factor (m = {})'
                          .format(round(m, 5)))

        # Create response sets for the view point.
        response_sets = {
            'x': self.get_response_set('float', 'm', self._view_point['x']),
            'y': self.get_response_set('float', 'm', self._view_point['y']),
            'z': self.get_response_set('float', 'm', self._view_point['z']),
            'stdDevX': self.get_response_set('float', 'm', sx),
            'stdDevY': self.get_response_set('float', 'm', sy),
            'stdDevZ': self.get_response_set('float', 'm', sz),
            'scaleFactor': self.get_response_set('float', 'm', m)
        }

        # Create observation instance of the view point.
        view_point = Observation()
        view_point.set('id', self._view_point.get('id'))
        view_point.set('name', 'getViewPoint')
        view_point.set('nextReceiver', 0)
        view_point.set('portName', obs.get('portName'))
        view_point.set('receivers', self._view_point.get('receivers'))
        view_point.set('responseSets', response_sets)
        view_point.set('timeStamp', time.time())

        # Return the observation of the view point.
        return view_point

    @staticmethod
    def _get_cartesian_coordinates(hz, v, slope_dist):
        hz_dist = slope_dist * math.sin(v)

        x = hz_dist * math.cos(hz)
        y = hz_dist * math.sin(hz)
        z = slope_dist * math.cos(v)

        return x, y, z

    def _is_tie_point(self, obs):
        """Checks if the given observation equals one of the defined tie
        points."""
        if self._tie_points.get(obs.get('id')):
            return True
        else:
            return False

    def _is_ready(self):
        """Checks whether all tie points have been measured already or not."""
        is_ready = True

        for tie_point_id, tie_point in self._tie_points.items():
            if tie_point.get('lastUpdate') is None:
                # Tie point has not been measured yet.
                is_ready = False
                break

        return is_ready

    def _update_tie_point(self, obs):
        """Adds horizontal direction, vertical angle, and slope distance
        of the observation to a tie point."""
        hz = obs.get_value('responseSets', 'hz', 'value')
        v = obs.get_value('responseSets', 'v', 'value')
        dist = obs.get_value('responseSets', 'slopeDist', 'value')

        if None in [hz, v, dist]:
            self.logger.warning('Hz, V, or distance is missing in observation '
                                '"{}" with ID "{}"'.format(obs.get('name'),
                                                           obs.get('id')))
            return obs

        # Calculate the coordinates of the tie point if the Helmert
        # transformation has already been done. Otherwise, use the datum from
        # the configuration.
        tie_point = self._tie_points.get(obs.get('id'))

        if self._is_ready():
            x, y, z = self._calculate_point_coordinates(
                hz,
                v,
                dist,
                self._view_point.get('x'),
                self._view_point.get('y'),
                self._view_point.get('z'),
                self._a,
                self._o)

            self.logger.info('Calculated coordinates of tie point "{}" '
                             '(X = {:3.5f}, Y = {:3.5f}, Z = {:3.5f})'
                             .format(obs.get('id'), x, y, z))
        else:
            # Get the coordinates of the tie point from the configuration.
            x = tie_point.get('x')
            y = tie_point.get('y')
            z = tie_point.get('z')

        # Update the values.
        tie_point['hz'] = hz
        tie_point['v'] = v
        tie_point['dist'] = dist
        tie_point['lastUpdate'] = time.time()

        self.logger.debug('Updated tie point "{}" (Hz = {:1.5f}, V = {:1.5f}, '
                          'Distance = {:3.5f}, Last Update = {})'
                          .format(obs.get('id'),
                                  tie_point['hz'],
                                  tie_point['v'],
                                  tie_point['dist'],
                                  tie_point['lastUpdate']))

        # Add global Cartesian coordinates of the tie point to the observation.
        response_sets = obs.get('responseSets')
        response_sets['x'] = self.get_response_set('float', 'm', x)
        response_sets['y'] = self.get_response_set('float', 'm', y)
        response_sets['z'] = self.get_response_set('float', 'm', z)

    def get_response_set(self, t, u, v):
        return {'type': t, 'unit': u, 'value': v}


class PolarTransformer(Prototype):
    """
    PolarTransformer calculates 3-dimensional coordinates of a target using the
    sensor position, and the azimuth position from the configuration together
    with the horizontal direction, the vertical angle, and the distance of a
    total station observation. The result (Y, X, Z) is added to the observation
    data set.
    """

    def __init__(self, name, config_manager, sensor_manager):
        Prototype.__init__(self, name, config_manager, sensor_manager)
        config = self._config_manager.config.get(self._name)

        self._sensor_x = config.get('sensorPosition').get('x')
        self._sensor_y = config.get('sensorPosition').get('y')
        self._sensor_z = config.get('sensorPosition').get('z')

        self._azimuth_x = config.get('azimuthPosition').get('x')
        self._azimuth_y = config.get('azimuthPosition').get('y')

    def process_observation(self, obs):
        sensor_type = obs.get('sensorType')

        if not SensorType.is_total_station(sensor_type.lower()):
            self.logger.error('Sensor type "{}" is not supported'
                              .format(sensor_type))
            return obs

        hz = obs.get_value('responseSets', 'hz', 'value')
        v = obs.get_value('responseSets', 'v', 'value')
        dist = obs.get_value('responseSets', 'slopeDist', 'value')

        if None in [hz, v, dist]:
            self.logger.warning('Hz, V, or distance is missing in observation '
                                '"{}" with ID "{}"'.format(obs.get('name'),
                                                           obs.get('id')))
            return obs

        # Radiant to grad (gon).
        hz_grad = hz * 200 / math.pi
        v_grad = v * 200 / math.pi

        self.logger.debug('Starting polar transformation of target "{}" (Hz = '
                          '{:3.5f} gon, V = {:3.5f} gon, dist = {:4.5f} m)'
                          .format(obs.get('id'), hz_grad, v_grad, dist))

        x, y, z = self.transform(self._sensor_x,
                                 self._sensor_y,
                                 self._sensor_z,
                                 self._azimuth_x,
                                 self._azimuth_y,
                                 hz,
                                 v,
                                 dist)

        self.logger.info('Transformed target "{}" (X = {:3.4f}, Y = {:3.4f}, '
                         'Z = {:3.4f})'.format(obs.get('id'), x, y, z))

        # Add to observation data set.
        response_sets = obs.get('responseSets')
        response_sets['x'] = self.get_response_set('float', 'm', round(x, 5))
        response_sets['y'] = self.get_response_set('float', 'm', round(y, 5))
        response_sets['z'] = self.get_response_set('float', 'm', round(z, 5))

        return obs

    def transform(self, sensor_x, sensor_y, sensor_z, azimuth_x, azimuth_y, hz,
                  v, dist):
        """Calculates coordinates (x, y, z) out of horizontal direction,
        vertical angle, and slope distance to a target point by doing a
        3-dimensional polar transformation."""
        # Calculate azimuth angle out of coordinates.
        d_x = azimuth_x - sensor_x
        d_y = azimuth_y - sensor_y
        azimuth = None

        if d_x == 0:
            if d_y > 0:
                azimuth = 0.5 * math.pi
            elif d_y < 0:
                azimuth = 1.5 * math.pi
            elif d_y == 0:
                self.logger.error('Sensor position equals azimuth')
        else:
            azimuth = math.atan(d_y / d_x)

        t = azimuth + hz

        if d_x < 0:
            t += math.pi

        if d_y < 0 < d_x:
            t += 2 * math.pi

        # Calculate coordinates of the target point.
        d_x = dist * math.sin(v) * math.cos(t)
        d_y = dist * math.sin(v) * math.sin(t)
        d_z = dist * math.cos(v)

        x = sensor_x + d_x
        y = sensor_y + d_y
        z = sensor_z + d_z

        return x, y, z

    def get_response_set(self, t, u, v):
        return {'type': t, 'unit': u, 'value': v}


class RefractionCorrector(Prototype):
    """
    RefractionCorrector removes the influence of the refraction from a measured
    distance and corrects the Z value of an observed target.
    """

    def __init__(self, name, config_manager, sensor_manager):
        Prototype.__init__(self, name, config_manager, sensor_manager)

    def process_observation(self, obs):
        z = obs.get_value('responseSets', 'z', 'value')

        if not z:
            self.logger.error('No height defined in observation "{}" with '
                              'ID "{}"'.format(obs.get('name'),
                                               obs.get('id')))
            return obs

        d = obs.get_value('responseSets', 'slopeDist', 'value')

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

        refraction = self.get_response_set('float', 'm', round(r, 6))
        z_new = self.get_response_set('float', 'm', round(z + r, 5))
        z_raw = self.get_response_set('float', 'm', z)

        obs.data['responseSets']['refraction'] = refraction
        obs.data['responseSets']['zRaw'] = z_raw
        obs.data['responseSets']['z'] = z_new

        return obs

    def get_response_set(self, t, u, v):
        return {'type': t, 'unit': u, 'value': v}


class SerialMeasurementProcessor(Prototype):
    """
    SerialMeasurementProcessor calculates serial measurements by using
    observations of one target in two faces. The two faces, consisting of
    horiontal directions, vertical angles, and slope distances, are
    averaged and stored in a new response set.
    """

    def __init__(self, name, config_manager, sensor_manager):
        Prototype.__init__(self, name, config_manager, sensor_manager)

    def process_observation(self, obs):
        # Calculate the serial measurement with two faces.
        hz_0 = obs.get_value('responseSets', 'hz0', 'value')
        hz_1 = obs.get_value('responseSets', 'hz1', 'value')

        v_0 = obs.get_value('responseSets', 'v0', 'value')
        v_1 = obs.get_value('responseSets', 'v1', 'value')

        dist_0 = obs.get_value('responseSets', 'slopeDist0', 'value')
        dist_1 = obs.get_value('responseSets', 'slopeDist1', 'value')

        if None in [hz_0, hz_1, v_0, v_1, dist_0, dist_1]:
            self.logger.warning('Hz, V, or distance is missing in observation '
                                '"{}" with ID "{}"'.format(obs.get('name'),
                                                           obs.get('id')))
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
        response_sets['hz'] = self.get_response_set('float', 'rad', hz)
        response_sets['v'] = self.get_response_set('float', 'rad', v)
        response_sets['slopeDist'] = self.get_response_set('float', 'm', dist)

        self.logger.debug('Calculated serial measurement with two faces for '
                          'observation "{}" with ID "{}"'
                          .format(obs.get('name'), obs.get('id')))

        return obs

    def get_response_set(self, t, u, v):
        return {'type': t, 'unit': u, 'value': v}
