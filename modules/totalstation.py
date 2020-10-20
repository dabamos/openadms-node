#!/usr/bin/env python3

"""Module for the processing of observations of total station positioning
systems (pre-processing, atmospheric corrections, transformations)."""

__author__ = 'Philipp Engel'
__copyright__ = 'Copyright (c) 2019 Hochschule Neubrandenburg'
__license__ = 'BSD-2-Clause'

import math
import time

from typing import Tuple, Union

import arrow

from core.observation import Observation as Obs
from core.manager import Manager
from core.sensor import SensorType
from core.util import gon_to_rad, rad_to_gon
from core.prototype import Prototype


class DistanceCorrector(Prototype):
    """
    Corrects the slope distance of EDM measurements using atmospheric data.

    The JSON-based configuration for this module:

    Parameters:
        atmosphericCorrectionEnabled (bool): Enables atmospheric correction.
        seaLevelCorrectionEnabled (bool): Enables correction to sea level.
        distanceName (str): Name of the response set.
        temperature (float): Default temperature (in °C).
        pressure (float): Default pressure (in hPa/mbar).
        humidity (float): Default humidity (0.0 ... 1.0).
        sensorHeight (float): Height of sensor.
    """

    def __init__(self, module_name: str, module_type: str, manager: Manager):
        super().__init__(module_name, module_type, manager)
        config = self.get_module_config(self._name)

        # Maximum age of atmospheric data, before a warning will be generated.
        self._max_age = 3600
        # TODO ... maybe should be better part of the configuration?

        self._is_atmospheric_correction = config.get('atmospheric'
                                                     'CorrectionEnabled')
        self._is_sea_level_correction = config.get('seaLevelCorrectionEnabled')

        self._distance_name = config.get('distanceName')
        self._temperature = config.get('temperature')
        self._pressure = config.get('pressure')
        self._humidity = config.get('humidity')
        self._sensor_height = config.get('sensorHeight')
        self._last_update = time.time()

    def process_observation(self, obs: Obs) -> Obs:
        sensor_type = obs.get('sensorType')

        # Update atmospheric data if sensor is a weather station.
        if SensorType.is_weather_station(sensor_type):
            self._update_meteorological_data(obs)
            return obs

        # Check if sensor is of type "total station".
        if not SensorType.is_total_station(sensor_type):
            self.logger.warning(f'Sensor type "{sensor_type}" not supported')
            return obs

        # Check the age of the atmospheric data.
        if self.last_update - time.time() > self._max_age:
            self.logger.warning(f'Atmospheric data is older than '
                                f'{int(self._max_age / 3600)} hour(s)')

        # Reduce the slope distance of the EDM measurement.
        dist = obs.get_response_value(self._distance_name)

        if dist is None:
            self.logger.error(f'No distance set in observation '
                              f'"{obs.get("name")}" of target '
                              f'"{obs.get("target")}"')
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

            rs = Obs.create_response_set('float', 'none', round(c, 5))
            response_sets['atmosphericPpm'] = rs

        # Calculate the sea level reduction of the distance.
        if self._is_sea_level_correction:
            d_dist_2 = self.get_sea_level_correction(self._sensor_height)

            rs = Obs.create_response_set('float', 'm', round(d_dist_2, 5))
            response_sets['seaLevelDelta'] = rs

        # Add corrected distance to the observation set.
        if d_dist_1 != 0 or d_dist_2 != 0:
            r_dist = dist + d_dist_1 + d_dist_2
            self.logger.info('Reduced distance from {:0.5f} m to {:0.5f} m '
                             '(correction value: {:0.5f} m)'
                             .format(dist, r_dist, d_dist_1 + d_dist_2))
            rs = Obs.create_response_set('float', 'm', round(r_dist, 5))

            response_sets[self._distance_name + 'Raw'] =\
                response_sets.get(self._distance_name)
            response_sets[self._distance_name] = rs

        return obs

    def get_atmospheric_correction(self,
                                   temperature: float,
                                   pressure: float,
                                   humidity: float) -> float:
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

    def get_sea_level_correction(self, sensor_height: float) -> float:
        """Calculates sea level correction value.

        Args:
            sensor_height: Height of sensor in metres.

        Returns:
            Correction value.
        """
        earth_radius = 6.378 * math.pow(10, 6)
        c = -1 * (sensor_height / earth_radius)

        return c

    def _update_meteorological_data(self, obs: Obs) -> None:
        """Updates the temperature, air pressure, and humidity attributes by
        using the measured data of a weather station."""
        # Update temperature.
        t = obs.get_response_value('temperature')

        if t is not None:
            self.temperature = t

        # Update pressure.
        p = obs.get_response_value('pressure')

        if p is not None:
            self.pressure = p

        # Update humidity.
        if (obs.has_response_value('humidity') and
            obs.has_response_type('humidity')):
            h = obs.get_response_value('humidity')
            u = obs.get_response_unit('humidity')

            self.humidity = h / 100 if u == '%' else h

    @property
    def temperature(self) -> float:
        return self._temperature

    @property
    def pressure(self) -> float:
        return self._pressure

    @property
    def humidity(self) -> float:
        return self._humidity

    @property
    def last_update(self) -> int:
        return self._last_update

    @property
    def sensor_height(self) -> float:
        return self._sensor_height

    @temperature.setter
    def temperature(self, temperature: float) -> None:
        """Sets the temperature."""
        self._temperature = temperature
        self._last_update = time.time()

        if temperature is not None:
            self.logger.verbose('Updated temperature to {:.2f} C'
                                .format(temperature))

    @pressure.setter
    def pressure(self, pressure: float) -> None:
        """Sets the air pressure."""
        self._pressure = pressure
        self._last_update = time.time()

        if pressure is not None:
            self.logger.verbose('Updated pressure to {:.2f} hPa'
                                .format(pressure))

    @humidity.setter
    def humidity(self, humidity: float) -> None:
        """Sets the humidity."""
        self._humidity = humidity
        self._last_update = time.time()

        if humidity is not None:
            self.logger.verbose('Updated humidity to {:.2f} %'
                                .format(humidity))

    @last_update.setter
    def last_update(self, last_update: int) -> None:
        """Sets the timestamp of the last update."""
        self._last_update = last_update

    @sensor_height.setter
    def sensor_height(self, sensor_height: float) -> None:
        """Sets the height of the sensor."""
        self._sensor_height = sensor_height


class HelmertTransformer(Prototype):
    """
    HelmertTransformer calculates the 3-dimensional coordinates of a view point
    using the Helmert transformation.

    The JSON-based configuration for this module:

    Parameters:
        residualMismatchTransformationEnabled (bool): If True, prorate
            residual mismatches.
        fixedPoints (Dict[Dict]): Coordinates of fixed points.
        viewPoint (Dict): Target name and receivers of view point.
    """

    def __init__(self, module_name: str, module_type: str, manager: Manager):
        super().__init__(module_name, module_type, manager)
        config = self.get_module_config(self._name)

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

    def process_observation(self, obs: Obs) -> Obs:
        """Calculates the coordinates of the view point and further target
        points by using the Helmert transformation. The given observation can
        either be of a fixed point or of a target point. Measured polar
        coordinates of the fixed points are used to determine the Cartesian
        coordinates of the view point and the given target points.

        An `Observation` object will be created for the view point and send
        to the receivers defined in the configuration.

        Args:
            obs: `Observation` object.

        Returns:
            The `Observation` object.
        """
        # Update the fixed point data of the configuration (Hz, V, slope
        # distance) by using the current observation.
        if self._is_fixed_point(obs):
            self._update_fixed_point(obs)

        # Only calculate the view point's and the target's coordinates if all
        # fixed points have been measured at least once.
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
                                    hz: float,
                                    v: float,
                                    dist: float,
                                    view_point_x: float,
                                    view_point_y: float,
                                    view_point_z: float,
                                    a: float,
                                    o: float) -> Tuple[float, float, float]:
        """Calculates Cartesian coordinates out of polar coordinates.

        Args:
            hz: Horizontal direction.
            v: Vertical angle.
            dist: Horizontal distance.
            view_point_x: X coordinate of the view point.
            view_point_y: Y coordinate of the view point.
            view_point_z: Z coordinate of the view point.
            a: Transformation parameter a.
            o: Transformation parameter o.

        Returns:
            Three-dimensional coordinates x, y, z.

        """
        local_x, local_y, local_z = self.get_cartesian_coordinates(hz,
                                                                   v,
                                                                   dist)
        x = view_point_x + (a * local_x) - (o * local_y)
        y = view_point_y + (a * local_y) + (o * local_x)
        z = view_point_z + local_z

        return x, y, z

    def _calculate_residual_mismatches(self,
                                       global_x: float,
                                       global_y: float) -> Tuple[float, float]:
        """Calculates the residual mismatches of view point coordinates due to
        redundant fixed points.

        Args:
            global_x: X coordinate of view point.
            global_y: Y coordinate of view point.

        Returns:
            Residual mismatches in x and y.
        """
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

    def _calculate_target_point(self, obs: Obs) -> Obs:
        """Calculates the coordinates of a target point and updates the
        given `Observation` object.

        Args:
            obs: `Observation` object.

        Returns:
            The `Observation` object with calculated coordinates.
        """
        hz = obs.get_response_value('hz')
        v = obs.get_response_value('v')
        dist = obs.get_response_value('slopeDist')

        if None in [hz, v, dist]:
            self.logger.warning(f'Hz, V, or distance missing in observation '
                                f'"{obs.get("name")}" of target '
                                f'"{obs.get("target")}"')
            return obs

        if dist == 0:
            self.logger.warning(f'Slope distance is "0" in observation '
                                f'"{obs.get("name")}" of target '
                                f'"{obs.get("target")}"')

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
                         '(X = {:4.5f}, Y = {:4.5f}, Z = {:4.5f})'
                         .format(obs.get("target"), x, y, z))

        # Do residual mismatch transformation.
        if self._is_residual:
            vx, vy = self._calculate_residual_mismatches(x, y)

            self.logger.debug('Calculated improvements for target point "{}" '
                              '(dX = {:4.5f} m, dY = {:4.5f} m)'
                              .format(obs.get("target"), vx, vy))

            x += vx
            y += vy

            self.logger.debug('Updated coordinates of target point "{}" '
                              '(X = {:4.5f}, Y = {:4.5f})'
                              .format(obs.get("target"), x, y))

        # Add response set.
        response_sets = obs.get('responseSets')
        response_sets['x'] = Obs.create_response_set('float', 'm', x)
        response_sets['y'] = Obs.create_response_set('float', 'm', y)
        response_sets['z'] = Obs.create_response_set('float', 'm', z)

        return obs

    def _calculate_view_point(self, obs: Obs) -> Union[Obs, None]:
        """Calculates the view point by doing a 2D Helmert transformation.

        Args:
            obs: `Observation` object. Needed for port and sensor information.

        Returns:
            New `Observation` object with view point coordinates.
        """
        sum_local_x = sum_local_y = sum_local_z = 0     # [x], [y], [z].
        sum_global_x = sum_global_y = sum_global_z = 0  # [X], [Y], [Z].
        num_fixed_points = len(self._fixed_points)      # n.

        # Calculate the centroid coordinates of the view point.
        for name, fixed_point in self._fixed_points.items():
            hz = fixed_point.get('hz')        # Horizontal direction.
            v = fixed_point.get('v')          # Vertical angle.
            dist = fixed_point.get('dist')    # Distance (slope or reduced).

            if None in [hz, v, dist]:
                self.logger.warning(f'Hz, V, or distance missing in fixed '
                                    f'point "{name}"')
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
                self.logger.error(f'Undefined fixed point "{name}"')

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
        self._view_point['x'] = (global_centroid_x -
            (self._a * local_centroid_x) + (self._o * local_centroid_y))
        self._view_point['y'] = (global_centroid_y -
            (self._a * local_centroid_y) - (self._o * local_centroid_x))
        self._view_point['z'] = (sum_global_z - sum_local_z) / num_fixed_points

        self.logger.info('Calculated coordinates of view point "{}" '
                         '(X = {:4.5f}, Y = {:4.5f}, Z = {:4.5f})'
                         .format(self._view_point.get('target'),
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

            wx_i = ((-1 * view_point_x) - (self._a * local_x) +
                    (self._o * local_y) + global_x)
            wy_i = ((-1 * view_point_y) - (self._a * local_y) -
                    (self._o * local_x) + global_y)

            sum_wx += wx_i
            sum_wy += wy_i

            sum_wx_wx += wx_i * wx_i
            sum_wy_wy += wy_i * wy_i
            sum_wz_wz += math.pow(view_point_z - (global_z - local_z), 2)

        # Sum of discrepancies should be 0, i.e., [W_x] = [W_y] = 0.
        r_sum_wx = abs(round(sum_wx, 5))
        r_sum_wy = abs(round(sum_wy, 5))

        if r_sum_wx != 0 or r_sum_wy != 0:
            self.logger.warning(f'Calculated coordinates of view point '
                                f'"{self._view_point.get("target")}" '
                                f'are inaccurate ([Wx] = {r_sum_wx}, '
                                f'[Wy] = {r_sum_wy})')

        # Standard deviations.
        sx = math.sqrt((sum_wx_wx + sum_wy_wy) / ((2 * num_fixed_points) - 4))
        sy = sx
        sz = math.sqrt(sum_wz_wz / (num_fixed_points - 1))

        self.logger.debug('Calculated standard deviations '
                          '(sX = {:1.5f} m, sY = {:1.5f} m, sZ = {:1.5f} m)'
                          .format(sx, sy, sz))

        # Scale factor.
        m = math.sqrt((self._a * self._a) + (self._o * self._o))
        self.logger.debug('Calculated scale factor (m = {:1.5f})'
                          .format(m))

        # Create response sets for the view point.
        response_sets = {
            'x': Obs.create_response_set('float', 'm', self._view_point['x']),
            'y': Obs.create_response_set('float', 'm', self._view_point['y']),
            'z': Obs.create_response_set('float', 'm', self._view_point['z']),
            'stdDevX': Obs.create_response_set('float', 'm', sx),
            'stdDevY': Obs.create_response_set('float', 'm', sy),
            'stdDevZ': Obs.create_response_set('float', 'm', sz),
            'scaleFactor': Obs.create_response_set('float', 'm', m)
        }

        # Create `Observation` instance for the view point.
        view_point = Obs()
        view_point.set('name', 'getViewPoint')
        view_point.set('nextReceiver', 0)
        view_point.set('nid', self._node_manager.node.id)
        view_point.set('portName', obs.get('portName'))
        view_point.set('pid', self._project_manager.project.id)
        view_point.set('receivers', self._view_point.get('receivers'))
        view_point.set('responseSets', response_sets)
        view_point.set('sensorName', obs.get('sensorName'))
        view_point.set('sensorType', obs.get('sensorType'))
        view_point.set('target', self._view_point.get('target'))
        view_point.set('timestamp', str(arrow.utcnow()))

        # Return the `Observation` object of the view point.
        return view_point

    def get_cartesian_coordinates(self,
                                  hz: float,
                                  v: float,
                                  slope_dist: float) -> Tuple[float,
                                                              float,
                                                              float]:
        """Returns Cartesian coordinates out of horizontal direction, vertical
        angle, and slope distance.

        Args:
            hz: Horizontal direction in rad.
            v: Vertical angle in rad.
            slope_dist: Slope distance in metres.

        Returns:
            Coordinates x, y, z.
        """
        hz_dist = slope_dist * math.sin(v)

        x = hz_dist * math.cos(hz)
        y = hz_dist * math.sin(hz)
        z = slope_dist * math.cos(v)

        return x, y, z

    def _is_fixed_point(self, obs: Obs) -> bool:
        """Checks if the given observation equals one of the defined fixed
        points."""
        if self._fixed_points.get(obs.get('target')):
            return True
        else:
            return False

    def _is_ready(self) -> bool:
        """Checks whether all fixed points have been measured at least once."""
        for fixed_point_id, fixed_point in self._fixed_points.items():
            if fixed_point.get('lastUpdate') is None:
                return False    # Fixed point has not been measured yet.

        return True

    def _update_fixed_point(self, obs: Obs) -> None:
        """Adds horizontal direction, vertical angle, and slope distance
        of the observation to a fixed point.

        Args:
            obs: `Observation` object.
        """
        hz = obs.get_response_value('hz')
        v = obs.get_response_value('v')
        dist = obs.get_response_value('slopeDist')

        if None in [hz, v, dist]:
            self.logger.warning(f'Hz, V, or distance missing in observation '
                                f'"{obs.get("name")}" of target '
                                f'"{obs.get("target")}"')
            return

        if dist == 0:
            self.logger.warning(f'Slope distance is "0" in observation '
                                f'"{obs.get("name")}" of target '
                                f'"{obs.get("target")}"')
            return

        # Calculate the coordinates of the fixed point if the Helmert
        # transformation has been done already. Otherwise, use the datum from
        # the configuration.
        fixed_point = self._fixed_points.get(obs.get('target'))

        if self._is_ready():
            # Calculate fixed point coordinates.
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
                             .format(obs.get("target"), x, y, z))
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

        self.logger.debug(f'Updated fixed point of target '
                          f'"{obs.get("target")}"')

        # Add global Cartesian coordinates of the fixed point to the
        # observation.
        response_sets = obs.get('responseSets')
        response_sets['x'] = Obs.create_response_set('float', 'm', x)
        response_sets['y'] = Obs.create_response_set('float', 'm', y)
        response_sets['z'] = Obs.create_response_set('float', 'm', z)


class PolarTransformer(Prototype):
    """
    PolarTransformer calculates 3-dimensional coordinates of a target using the
    sensor position and the azimuth position from the configuration together
    with the horizontal direction, the vertical angle, and the distance of a
    total station observation. The result (Y, X, Z) is added to the observation
    data set.

    It is possible to use multiple fixed points in order to improve the
    accuracy of the horizontal directions ('Abriss' in German).

    The JSON-based configuration for this module:

    Parameters:
        adjustmentEnabled (bool): If True, improve horizontal directions.
        azimuthAngle (float): Between local and global azimuth (in gon).
        azimuthPointName (str): Name of azimuth.
        fixedPoints (Dict[Dict]): Coordinates of fixed points (X, Y, Z).
        viewPoint (Dict): Coordinates of view point (X, Y, Z).
    """

    def __init__(self, module_name: str, module_type: str, manager: Manager):
        super().__init__(module_name, module_type, manager)
        config = self.get_module_config(self._name)

        self._view_point = config.get('viewPoint')
        self._fixed_points = config.get('fixedPoints')

        self._azimuth_point_name = config.get('azimuthPointName')
        self._azimuth_point = self._fixed_points.get(self._azimuth_point_name)

        if not self._azimuth_point:
            self.logger.error(f'Undefined azimuth point '
                              f'"{self._azimuth_point_name}"')

        self._azimuth_angle = gon_to_rad(config.get('azimuthAngle', 0))
        self._is_adjustment_enabled = config.get('adjustmentEnabled')

    def _get_adjustment_value(self) -> float:
        """Returns the adjustment value for the improvement of horizontal
        directions.

        Returns:
            The adjustment value.
        """
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

    def _is_fixed_point(self, obs: Obs) -> bool:
        """Checks if the given observation equals one of the defined fixed
        points.

        Args:
            obs: `Observation` object.

        Returns:
            True if observation is fixed point, False if not.
        """
        if self._fixed_points.get(obs.get('target')):
            return True
        else:
            return False

    def _is_valid_sensor_type(self, obs: Obs) -> bool:
        """Returns whether or not the sensor is supported.

        Args:
            obs: `Observation` object.

        Returns:
            True if sensor is supported, False if not.
        """
        sensor_type = obs.get('sensorType')

        if not SensorType.is_total_station(sensor_type):
            self.logger.error(f'Sensor type "{sensor_type}" not supported')
            return False

        return True

    def _update_fixed_point(self, obs: Obs) -> None:
        """Updates given fixed point.

        Args:
            obs: `Observation` object.
        """
        fixed_point = self._fixed_points.get(obs.get('target'))
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
                          view_point_azimuth: float,
                          view_point_x: float,
                          view_point_y: float,
                          target_point_x: float,
                          target_point_y: float) -> float:
        """Calculates the azimuth angle to a target point by using the
        direction and the distance measured from a given view point.

        Args:
            view_point_azimuth: Global azimuth.
            view_point_x: X coordinate of view point.
            view_point_y: Y coordinate of view point.
            target_point_x: X coordinate of target point.
            target_point_y: Y coordinate of target point.

        Returns:
            The azimuth angle to target point.
        """
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

    def process_observation(self, obs: Obs) -> Obs:
        if not self._is_valid_sensor_type(obs):
            # Only total stations are supported.
            return obs

        hz = obs.get_response_value('hz')
        v = obs.get_response_value('v')
        dist = obs.get_response_value('slopeDist')

        if None in [hz, v, dist]:
            self.logger.warning(f'Hz, V, or distance missing in observation '
                                f'"{obs.get("name")}" of target '
                                f'"{obs.get("target")}"')
            return obs

        if dist == 0:
            self.logger.warning(f'Slope distance is "0" in observation '
                                f'"{obs.get("name")}" of target '
                                f'"{obs.get("target")}"')

        # Calculate the horizontal distance.
        dist_hz = math.sin(v) * dist

        if self._is_fixed_point(obs):
            # Add measured Hz and calculated Hz to the fixed point.
            self._update_fixed_point(obs)
            self.logger.debug(f'Updated fixed point of target '
                              f'"{obs.get("target")}"')

        self.logger.debug('Starting polar transformation of target "{}" (Hz = '
                          '{:3.5f} gon, V = {:3.5f} gon, dist = {:4.5f} m)'
                          .format(obs.get("target"),
                                  rad_to_gon(hz),
                                  rad_to_gon(v),
                                  dist_hz))

        if self._is_adjustment_enabled:
            # Add the adjustment value to the horizontal direction.
            adj = self._get_adjustment_value()
            self.logger.info('Calculated adjustment value for polar '
                             'transformation ({:3.5f} gon)'
                             .format(rad_to_gon(adj)))
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
                         'Z = {:3.4f})'.format(obs.get("target"), x, y, z))

        # Add to observation data set.
        response_sets = obs.get('responseSets')
        response_sets['x'] = Obs.create_response_set('float', 'm', round(x, 5))
        response_sets['y'] = Obs.create_response_set('float', 'm', round(y, 5))
        response_sets['z'] = Obs.create_response_set('float', 'm', round(z, 5))

        if self._is_adjustment_enabled:
            response_sets['hzAdjusted'] = Obs.create_response_set(
                'float', 'rad', round(hz, 16))

        return obs

    def transform(self,
                  view_point_x: float,
                  view_point_y: float,
                  view_point_z: float,
                  target_point_x: float,
                  target_point_y: float,
                  hz: float,
                  v: float,
                  dist: float) -> Tuple[float, float, float]:
        """Calculates coordinates (x, y, z) out of horizontal direction,
        vertical angle, and slope distance to a target point using a
        3-dimensional polar transformation.

        Args:
            view_point_x: X coordinate of view point.
            view_point_y: Y coordinate of view point.
            view_point_z: Z coordinate of view point.
            target_point_x: X coordinate of target point.
            target_point_y: Y coordinate of target point.
            hz: Horizontal direction between view point and target point.
            v: Vertical angle between view point and target point.
            dist: Horizontal distance between view point and target point.

        Returns:
            X, Y, and Z coordinates of transformed target.
        """
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


class RefractionCorrector(Prototype):
    """
    RefractionCorrector removes the influence of the refraction from a measured
    distance and corrects the Z value of an observed target.

    The module has nothing to configure.
    """

    def __init__(self, module_name: str, module_type: str, manager: Manager):
        super().__init__(module_name, module_type, manager)

    def process_observation(self, obs: Obs) -> Obs:
        z = obs.get_response_value('z')

        if not z:
            return obs

        d = obs.get_response_value('slopeDist')

        if d is None:
            self.logger.error(f'Slope distance is missing in observation '
                              f'"{obs.get("name")}" of target '
                              f'"{obs.get("target")}"')
            return obs

        if d == 0:
            self.logger.warning(f'Slope distance is "0" in observation '
                                f'"{obs.get("name")}" of target '
                                f'"{obs.get("target")}"')

        k = 0.13                    # Refraction coefficient.
        r = 6370000                 # Earth radius.

        k_e = (d * d) / (2 * r)     # Correction of earth radius.
        k_r = k * k_e               # Correction of refraction.
        r = k_e - k_r

        self.logger.info('Updated height in observation "{}" of target "{}" '
                         'from {:3.4f} m to {:3.4f} m (refraction value: '
                         '{:3.5f} m)'.format(obs.get("name"),
                                             obs.get("target"),
                                             z,
                                             z + r,
                                             r))

        refraction = Obs.create_response_set('float', 'm', round(r, 6))
        z_new = Obs.create_response_set('float', 'm', round(z + r, 5))
        z_raw = Obs.create_response_set('float', 'm', z)

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

    The module has nothing to configure.
    """

    def __init__(self, module_name: str, module_type: str, manager: Manager):
        super().__init__(module_name, module_type, manager)

    def process_observation(self, obs: Obs) -> Obs:
        # Calculate the serial measurement of an observation in two faces.
        hz0 = obs.get_response_value('hz0')
        hz1 = obs.get_response_value('hz1')

        v0 = obs.get_response_value('v0')
        v1 = obs.get_response_value('v1')

        dist0 = obs.get_response_value('slopeDist0')
        dist1 = obs.get_response_value('slopeDist1')

        if None in [hz0, hz1, v0, v1, dist0, dist1]:
            self.logger.warning(f'Hz, V, or distance missing in observation '
                                f'"{obs.get("name")}" of target '
                                f'"{obs.get("target")}"')
            return obs

        # Calculate new Hz, V, and slope distance.
        hz = hz0 + hz1

        if hz0 > hz1:
            hz += math.pi
        else:
            hz -= math.pi

        hz /= 2
        v = ((2 * math.pi) + (v0 - v1)) / 2
        dist = 0

        if (dist0 != 0 and dist1 != 0):
            dist = (dist0 + dist1) / 2

        # Save the calculated values.
        response_sets = obs.get('responseSets')
        response_sets['hz'] = Obs.create_response_set('float', 'rad', hz)
        response_sets['v'] = Obs.create_response_set('float', 'rad', v)
        response_sets['slopeDist'] = Obs.create_response_set('float', 'm', dist)

        self.logger.debug(f'Calculated serial measurement with two faces for '
                          f'observation "{obs.get("name")}" of target '
                          f'"{obs.get("target")}"')
        return obs

