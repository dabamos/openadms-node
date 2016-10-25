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
import time

from core.observation import Observation
from core.sensor import SensorType
from modules.prototype import Prototype

"""Module for data processing (pre-processing, atmospheric corrections,
transformations)."""

logger = logging.getLogger('openadms')


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

        self._is_atmospheric_correction = \
            config.get('AtmosphericCorrectionEnabled')
        self._is_sea_level_correction = \
            config.get('SeaLevelCorrectionEnabled')

        self._distance_name = config.get('DistanceName')
        self._temperature = config.get('Temperature')
        self._pressure = config.get('Pressure')
        self._humidity = config.get('Humidity')
        self._sensor_height = config.get('SensorHeight')
        self._last_update = time.time()

    def process_observation(self, obs):
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
            logger.warning('No temperature, air pressure, or humidity set')
            return obs

        # Check the age of the atmospheric data.
        if self.last_update - time.time() > self._max_age:
            logger.warning('Atmospheric data is older than {} hour(s)'
                           .format(int(self._max_age / 3600)))

        # Reduce the slope distance of the EDM measurement if the sensor is a
        # robotic total station.
        dist = obs.get_value('ResponseSets', self._distance_name, 'Value')

        if dist is None:
            return obs

        d_dist_1 = 0
        d_dist_2 = 0

        response_sets = obs.get('ResponseSets')

        # Calculate the atmospheric reduction of the distance.
        if self._is_atmospheric_correction:
            ppm = self.get_ppm()
            d_dist_1 = dist * ppm * math.pow(10, -6)

            response_set = self.get_response_set('Float',
                                                 'none',
                                                 round(ppm, 5))
            response_sets['AtmosphericPPM'] = response_set

        # Calculate the sealevel reduction of the distance.
        if self._is_sea_level_correction:
            earth_radius = 6.378 * math.pow(10, 6)
            # Delta distance: -(height / R) * 10^6
            d_dist_2 = -1 * (self.sensor_height / earth_radius)

            response_set = self.get_response_set('Float',
                                                 'm',
                                                 round(d_dist_2, 5))
            response_sets['SeaLevelDelta'] = response_set

        # Add reduced distance to the observation set.
        if d_dist_1 != 0 or d_dist_2 != 0:
            r_dist = dist + d_dist_1 + d_dist_2

            logger.info('Reduced distance from {:0.5f} m to {:0.5f} m '
                        '({:0.5f} m)'.format(dist,
                                             r_dist,
                                             d_dist_1 + d_dist_2))

            response_set = self.get_response_set('Float',
                                                 'm',
                                                 round(r_dist, 5))

            response_sets['Raw' + self._distance_name] =\
                response_sets.get(self._distance_name)
            response_sets[self._distance_name] = response_set

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

        a = 0.29525 * self.pressure
        b = 4.126 * math.pow(10, -4) * self.humidity

        ppm = 286.34 - ((a / div) - ((b / div) * math.pow(10, int(x))))

        return ppm

    def _update_meteorological_data(self, obs):
        """Updates the temperature, air pressure, and humidity attributes by
        using the measured data of a weather station."""
        try:
            t = obs.get('ResponseSets').get('Temperature').get('Value')
            self.temperature = t
        except AttributeError:
            pass

        try:
            p = obs.get('ResponseSets').get('Pressure').get('Value')
            self.pressure = p
        except AttributeError:
            pass

        try:
            h = obs.get('ResponseSets').get('Humidity').get('Value')
            u = obs.get('ResponseSets').get('Humidity').get('Unit')

            if h is not None and u is not None:
                self.humidity = h / 100 if u == '%' else h
        except AttributeError:
            pass

    def get_response_set(self, t, u, v):
        return {'Type': t, 'Unit': u, 'Value': v}

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

        self._tie_points = config.get('TiePoints')
        self._view_point = config.get('ViewPoint')
        # self._sensor_height = config.get('ViewPoint').get('SensorHeight')

        # Initialize view point.
        self._view_point['X'] = 0
        self._view_point['Y'] = 0
        self._view_point['Z'] = 0

        self._is_ready = False

        self._a = None
        self._o = None

        self._is_residual = config.get('ResidualMismatchTransformationEnabled')

    def process_observation(self, obs):
        """Calculates the coordinates of the view point and further target
        points by using the Helmert transformation. The given observation can
        either be of a tie point or of a target point.

        Measured polar coordinates of the tie points are used to determine the
        Cartesian coordinates of the view point and given target points.

        An `Observation` object will be created for the view point and send
        to the receivers defined in the configuration."""
        is_tie_point = False

        # Check if the given observation equals one of the defined tie points.
        if self._tie_points.get(obs.get('ID')):
            is_tie_point = True

        # Update the tie point data (Hz, V, slope distance).
        if is_tie_point:
            self._update_tie_point(obs)

        # Only calculate the view point's coordinates if all tie points have
        # been measured at least once.
        self._is_ready = True

        for tie_point_id, tie_point in self._tie_points.items():
            if tie_point.get('LastUpdate') is None:
                # Tie point has not been measured yet.
                self._is_ready = False

        if self._is_ready:
            if is_tie_point:
                # Calculate the coordinates of the view point by using the
                # Helmert transformation and create a new observation of the
                # view point.
                view_point = self._calculate_view_point(obs)

                # Send the new view point observation to the next receiver.
                if view_point:
                    # Get the name of the next receiver.
                    index = view_point.get('NextReceiver')
                    receivers = view_point.get('Receivers')
                    next_receiver = receivers[index]
                    index += 1
                    view_point.set('NextReceiver', index)

                    # Create target, header, and payload in order to send the observation.
                    target = next_receiver
                    header = {'Type': 'Observation'}
                    payload = view_point.data

                    # Fire and forget.
                    self.publish(target, header, payload)
            else:
                # Calculate the coordinates of the target point.
                obs = self._calculate_target_point(obs)

        return obs

    def _calculate_point_coordinates(self, hz, v, dist, view_point_x,
                                     view_point_y, view_point_z, a, o):
        hz_dist = dist * math.sin(v)

        # Calculate Cartesian coordinates using Polar coordinates (x, y, z).
        local_x = hz_dist * math.cos(hz)
        local_y = hz_dist * math.sin(hz)
        local_z = dist * math.cos(v)

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
            a = math.pow(global_x - tie_point.get('X'), 2)
            b = math.pow(global_y - tie_point.get('Y'), 2)
            s = math.sqrt(a + b)
            p = 1 / s

            # Global Cartesian coordinates of the tie point.
            x, y, z = self._calculate_point_coordinates(
                tie_point.get('Hz'),
                tie_point.get('V'),
                tie_point.get('Dist'),
                self._view_point.get('X'),
                self._view_point.get('Y'),
                self._view_point.get('Z'),
                self._a,
                self._o)

            vx = tie_point.get('X') - x
            vy = tie_point.get('Y') - y

            sum_p_vx += p * vx
            sum_p_vy += p * vy
            sum_p += p

        vx = sum_p_vx / sum_p
        vy = sum_p_vy / sum_p

        return vx, vy

    def _calculate_target_point(self, obs):
        hz = obs.get_value('ResponseSets', 'Hz', 'Value')
        v = obs.get_value('ResponseSets', 'V', 'Value')
        dist = obs.get_value('ResponseSets', 'SlopeDist', 'Value')

        if None in [hz, v, dist]:
            logger.warning('Hz, V, or distance missing in observation "{}" '
                           'with ID "{}"'.format(obs.get('Name'),
                                                 obs.get('ID')))
            return obs

        # Calculate the coordinates in the global system (X, Y, Z).
        x, y, z = self._calculate_point_coordinates(
            hz,
            v,
            dist,
            self._view_point.get('X'),
            self._view_point.get('Y'),
            self._view_point.get('Z'),
            self._a,
            self._o)

        logger.info('Calculated coordinates of target point "{}" '
                    '(X = {}, Y = {}, Z = {})'.format(obs.get('ID'),
                                                      round(x, 5),
                                                      round(y, 5),
                                                      round(z, 5)))

        # Do residual mismatch transformation.
        if self._is_residual:
            vx, vy = self._calculate_residual_mismatches(x, y)

            logger.debug('Calculated improvements for target point "{}" '
                         '(x = {:4.5f} m, y = {:4.5f} m)'.format(obs.get('ID'),
                                                                 vx,
                                                                 vy))

            x += vx
            y += vy

            logger.debug('Updated coordinates of target point "{}" '
                         '(X = {:4.5f}, Y = {:4.5f})'.format(obs.get('ID'),
                                                             x,
                                                             y))

        # Add response set.
        response_sets = obs.get('ResponseSets')
        response_sets['X'] = self.get_response_set('Float', 'm', x)
        response_sets['Y'] = self.get_response_set('Float', 'm', y)
        response_sets['Z'] = self.get_response_set('Float', 'm', z)

        return obs

    def _calculate_view_point(self, obs):
        sum_local_x = sum_local_y = sum_local_z = 0     # [x], [y], [z].
        sum_global_x = sum_global_y = sum_global_z = 0  # [X], [Y], [Z].
        num_tie_points = len(self._tie_points)          # n.

        # Calculate the centroid coordinates of the view point.
        for name, tie_point in self._tie_points.items():
            hz = tie_point.get('Hz')        # Horizontal direction.
            v = tie_point.get('V')          # Vertical angle.
            dist = tie_point.get('Dist')    # Distance (slope or reduced).

            if None in [hz, v, dist]:
                logger.warning('Hz, V, or distance missing in observation "{}" '
                               'with ID "{}"'.format(obs.get('Name'),
                                                     obs.get('ID')))
                return

            # Calculate horizontal distance out of slope distance and
            # vertical angle.
            hz_dist = dist * math.sin(v)

            # Coordinates in the local system (x, y, z).
            local_x = hz_dist * math.cos(hz)
            local_y = hz_dist * math.sin(hz)
            local_z = dist * math.cos(v)

            # Store local coordinates in the tie point dictionary.
            tie_point['x'] = local_x
            tie_point['y'] = local_y
            tie_point['z'] = local_z

            # Coordinates in the global system (X, Y, Z).
            global_x = tie_point.get('X')
            global_y = tie_point.get('Y')
            global_z = tie_point.get('Z')

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
            local_x = tie_point.get('x')
            local_y = tie_point.get('y')

            global_x = tie_point.get('X')
            global_y = tie_point.get('Y')

            # Reduced coordinates of the centroids.
            r_local_centroid_x = local_x - local_centroid_x
            r_local_centroid_y = local_y - local_centroid_y

            r_global_centroid_x = global_x - global_centroid_x
            r_global_centroid_y = global_y - global_centroid_y

            # o = [ x_i * Y_i - y_i * X_i ] * [ x_i^2 + y_i^2 ]^-1
            o_1 += (r_local_centroid_x * r_global_centroid_y) - \
                   (r_local_centroid_y * r_global_centroid_x)
            o_2 += math.pow(r_local_centroid_x, 2) + \
                   math.pow(r_local_centroid_y, 2)

            # a = [ x_i * X_i + y_i * Y_i ] * [ x_i^2 + y_i^2 ]^-1
            a_1 += (r_local_centroid_x * r_global_centroid_x) + \
                   (r_local_centroid_y * r_global_centroid_y)
            a_2 += math.pow(r_local_centroid_x, 2) + \
                   math.pow(r_local_centroid_y, 2)

        self._o = o_1 / o_2  # Parameter o.
        self._a = a_1 / a_2  # Parameter a.

        # Calculate the coordinates of the view point:
        # Y_0 = Y_s - a * y_s - o * x_s
        # X_0 = X_s - a * x_s + o * y_s
        # Z_0 = ([Z] - [z]) / n
        self._view_point['X'] = global_centroid_x -\
                                (self._a * local_centroid_x) +\
                                (self._o * local_centroid_y)
        self._view_point['Y'] = global_centroid_y -\
                                (self._a * local_centroid_y) -\
                                (self._o * local_centroid_x)
        self._view_point['Z'] = (sum_global_z - sum_local_z) / num_tie_points

        logger.info('Calculated coordinates of view point "{}" '
                    '(X = {:4.5f}, Y = {:4.5f}, Z = {:4.5f})'
                    .format(self._view_point.get('ID'),
                            self._view_point.get('X'),
                            self._view_point.get('Y'),
                            self._view_point.get('Z')))

        # Calculate the standard deviations.
        sum_wx = sum_wy = 0  # [W_x], [W_y].
        sum_wx_wx = sum_wy_wy = sum_wz_wz = 0  # [W_x^2], [W_y^2], [W_z^2].

        for name, tie_point in self._tie_points.items():
            local_x = tie_point.get('x')
            local_y = tie_point.get('y')
            local_z = tie_point.get('z')

            global_x = tie_point.get('X')
            global_y = tie_point.get('Y')
            global_z = tie_point.get('Z')

            view_point_x = self._view_point.get('X')
            view_point_y = self._view_point.get('Y')
            view_point_z = self._view_point.get('Z')

            wx_i = (-1 * view_point_x) - (self._a * local_x) + \
                   (self._o * local_y) + global_x
            wy_i = (-1 * view_point_y) - (self._a * local_y) - \
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
            logger.warning('Calculated coordinates of view point "{}" are '
                           'inaccurate ([W_x] = {}, [W_y] = {})'
                           .format(self._view_point.get('ID'),
                                   r_sum_wx,
                                   r_sum_wy))

        # Standard deviations.
        sx = math.sqrt((sum_wx_wx + sum_wy_wy) / ((2 * num_tie_points) - 4))
        sy = sx
        sz = math.sqrt(sum_wz_wz / (num_tie_points - 1))

        logger.debug('Calculated standard deviations '
                     '(s_x = {:1.5f} m, s_y = {:1.5f} m, s_z = {:1.5f} m)'
                     .format(sx, sy, sz))

        # Scale factor.
        m = math.sqrt((self._a * self._a) + (self._o * self._o))
        logger.debug('Calculated scale factor (m = {})'.format(round(m, 5)))

        # Create response sets for the view point.
        response_sets = {
            'X': self.get_response_set('Float', 'm', self._view_point['X']),
            'Y': self.get_response_set('Float', 'm', self._view_point['Y']),
            'Z': self.get_response_set('Float', 'm', self._view_point['Z']),
            'StdDevX': self.get_response_set('Float', 'm', sx),
            'StdDevY': self.get_response_set('Float', 'm', sy),
            'StdDevZ': self.get_response_set('Float', 'm', sz),
            'ScaleFactor': self.get_response_set('Float', 'm', m)
        }

        # Create observation instance of the view point.
        view_point = Observation()
        view_point.set('ID', self._view_point.get('ID'))
        view_point.set('Name', 'get_view_point')
        view_point.set('NextReceiver', 0)
        view_point.set('PortName', obs.get('PortName'))
        view_point.set('Receivers', self._view_point.get('Receivers'))
        view_point.set('ResponseSets', response_sets)
        view_point.set('TimeStamp', time.time())

        # Return the observation of the view point.
        return view_point

    def _update_tie_point(self, obs):
        """Adds horizontal direction, vertical angle, and slope distance
        of the observation to a tie point."""
        hz = obs.get_value('ResponseSets', 'Hz', 'Value')
        v = obs.get_value('ResponseSets', 'V', 'Value')
        dist = obs.get_value('ResponseSets', 'SlopeDist', 'Value')

        if None in [hz, v, dist]:
            logger.warning('Hz, V, or distance missing in observation "{}" '
                           'with ID "{}"'.format(obs.get('Name'),
                                                 obs.get('ID')))
            return obs

        now = time.time()

        # Set the values.
        tie_point = self._tie_points.get(obs.get('ID'))
        tie_point['Hz'] = hz
        tie_point['V'] = v
        tie_point['Dist'] = dist
        tie_point['LastUpdate'] = now

        logger.debug('Updated tie point "{}" (Hz = {:1.5f}, V = {:1.5f}, '
                     'Dist = {:3.5f}, LastUpdate = {})'.format(obs.get('ID'),
                                                               hz,
                                                               v,
                                                               dist,
                                                               now))

        # Calculate the coordinates of the tie point if the Helmert
        # transformation has already been done. Otherwise, use the datum from
        # the configuration.
        if self._is_ready:
            x, y, z = self._calculate_point_coordinates(
                tie_point.get('Hz'),
                tie_point.get('V'),
                tie_point.get('Dist'),
                self._view_point.get('X'),
                self._view_point.get('Y'),
                self._view_point.get('Z'),
                self._a,
                self._o)

            logger.info('Calculated coordinates of tie point "{}" '
                        '(X = {:3.5f}, Y = {:3.5f}, Z = {:3.5f})'
                        .format(obs.get('ID'), x, y, z))
        else:
            # Get the coordinates of the tie point from the configuration.
            x = tie_point.get('X')
            y = tie_point.get('Y')
            z = tie_point.get('Z')

        # Add global Cartesian coordinates of the tie point to the observation.
        response_sets = obs.get('ResponseSets')
        response_sets['X'] = self.get_response_set('Float', 'm', x)
        response_sets['Y'] = self.get_response_set('Float', 'm', y)
        response_sets['Z'] = self.get_response_set('Float', 'm', z)

    def get_response_set(self, t, u, v):
        return {'Type': t, 'Unit': u, 'Value': v}


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

        self._sensor_x = config.get('SensorPosition').get('X')
        self._sensor_y = config.get('SensorPosition').get('Y')
        self._sensor_z = config.get('SensorPosition').get('Z')

        self._azimuth_x = config.get('AzimuthPosition').get('X')
        self._azimuth_y = config.get('AzimuthPosition').get('Y')

    def process_observation(self, obs):
        sensor_type = obs.get('SensorType')

        if not SensorType.is_total_station(sensor_type.lower()):
            logger.error('Sensor type "{}" is not supported'
                         .format(sensor_type))
            return obs

        hz = obs.get_value('ResponseSets', 'Hz', 'Value')
        v = obs.get_value('ResponseSets', 'V', 'Value')
        dist = obs.get_value('ResponseSets', 'SlopeDist', 'Value')

        if None in [hz, v, dist]:
            logger.warning('Hz, V, or distance missing in observation "{}" '
                           'with ID "{}"'.format(obs.get('Name'),
                                                 obs.get('ID')))
            return obs

        # Radiant to grad (gon).
        hz_grad = hz * 200 / math.pi
        v_grad = v * 200 / math.pi

        logger.debug('Starting polar transformation of target "{}" with '
                     '(Hz = {:3.5f} gon, V = {:3.5f} gon, dist = {:4.5f} m)'
                     .format(obs.get('ID'),
                             hz_grad,
                             v_grad,
                             dist))

        (x, y, z) = self.transform(self._sensor_x,
                                   self._sensor_y,
                                   self._sensor_z,
                                   self._azimuth_x,
                                   self._azimuth_y,
                                   hz,
                                   v,
                                   dist)

        logger.info('Transformed target "{}" (X = {:3.4f}, Y = {:3.4f}, '
                    'Z = {:3.4f})'.format(obs.get('ID'),
                                          x,
                                          y,
                                          z))

        # Add to observation data set.
        response_sets = obs.get('ResponseSets')
        response_sets['X'] = self.get_response_set('Float', 'm', round(x, 5))
        response_sets['Y'] = self.get_response_set('Float', 'm', round(y, 5))
        response_sets['Z'] = self.get_response_set('Float', 'm', round(z, 5))

        return obs

    def transform(self, sensor_x, sensor_y, sensor_z, azimuth_x, azimuth_y, hz,
                  v, dist):
        """Calculates coordinates (X, Y, Z) out of horizontal direction,
        vertical angle, and slope distance to a target point by doing a
        3-dimensional polar transformation."""
        # Calculate azimuth angle out of coordinates.
        d_x = azimuth_x - sensor_x
        d_y = azimuth_y - sensor_y

        if d_x == 0:
            if d_y > 0:
                azimuth = 0.5 * math.pi
            elif d_y < 0:
                azimuth = 1.5 * math.pi
            elif d_y == 0:
                logger.error('Sensor position equals azimuth')
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
        return {'Type': t, 'Unit': u, 'Value': v}


class SerialMeasurementProcessor(Prototype):

    def __init__(self, name, config_manager, sensor_manager):
        Prototype.__init__(self, name, config_manager, sensor_manager)

    def process_observation(self, obs):
        # Calculate the serial measurement with two faces.
        hz_0 = obs.get_value('ResponseSets', 'Hz0', 'Value')
        hz_1 = obs.get_value('ResponseSets', 'Hz1', 'Value')
        v_0 = obs.get_value('ResponseSets', 'V0', 'Value')
        v_1 = obs.get_value('ResponseSets', 'V1', 'Value')
        dist_0 = obs.get_value('ResponseSets', 'SlopeDist0', 'Value')
        dist_1 = obs.get_value('ResponseSets', 'SlopeDist1', 'Value')

        if None in [hz_0, hz_1, v_0, v_1, dist_0, dist_1]:
            logger.warning('Hz, V, or distance missing in observation "{}" '
                           'with ID "{}"'.format(obs.get('Name'),
                                                 obs.get('ID')))
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

        # logger.info('<<< Hz0 = {}, V0 = {} >>>'.format(hz_0, v_0))
        # logger.info('<<< Hz1 = {}, V1 = {} >>>'.format(hz_1, v_1))
        # logger.info('<<< Hz = {}, V = {} >>>'.format(hz, v))

        # Save the calculated values.
        response_sets = obs.get('ResponseSets')
        response_sets['Hz'] = self.get_response_set('Float', 'rad', hz)
        response_sets['V'] = self.get_response_set('Float', 'rad', v)
        response_sets['SlopeDist'] = self.get_response_set('Float', 'm', dist)

        logger.info('Calculated serial measurement with two faces for '
                    'observation "{}" with ID "{}"'.format(obs.get('Name'),
                                                           obs.get('ID')))

        return obs

    def get_response_set(self, t, u, v):
        return {'Type': t, 'Unit': u, 'Value': v}
