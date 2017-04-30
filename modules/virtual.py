#!/usr/bin/env python3
"""
Copyright (c) 2016 Hochschule Neubrandenburg.

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

import math
import random
import re
import time

from modules.prototype import Prototype

"""Module for virtual sensors."""


class VirtualSensor(Prototype):
    """
    VirtualSensor is a prototype class for virtual sensors.
    """

    def __init__(self, name, type, managers):
        Prototype.__init__(self, name, type, managers)
        self.patterns = {}

    def process_observation(self, obs):
        request_sets = obs.get('requestSets')

        for set_name, request_set in request_sets.items():
            request = request_set.get('request')
            timeout = request_set.get('timeout')
            sleep_time = request_set.get('sleepTime')
            response = ''

            self.logger.info('Sending request "{}" to sensor "{}" on virtual '
                             'port "{}"'.format(set_name,
                                                obs.get('sensorName'),
                                                self.name))

            for pattern in self.patterns:
                reg_exp = re.compile(pattern)
                parsed = reg_exp.match(request)

                if not parsed:
                    continue

                response = self.patterns[pattern](request)

                self.logger.info('Received response "{}" from sensor "{}" on '
                                 'virtual port "{}"'
                                 .format(self.sanitize(response),
                                         obs.get('sensorName'),
                                         self.name))
                break

            request_set['response'] = response
            time.sleep((timeout * 0.25) + sleep_time)

        obs.set('portName', self._name)
        obs.set('timeStamp', time.time())

        return obs

    def sanitize(self, s):
        """Converts some non-printable characters of a given string."""
        return s.replace('\n', '\\n')\
                .replace('\r', '\\r')\
                .replace('\t', '\\t')\
                .strip()


class VirtualTotalStationTM30(VirtualSensor):
    """
    VirtualTotalStationTM30 simulates a Leica TM30 totalstation by processing
    GeoCOM commands.
    """

    def __init__(self, name, type, managers):
        VirtualSensor.__init__(self, name, type, managers)

        self.patterns = {
            '%R1Q,5003:\\r\\n': self.get_sensor_id,
            '%R1Q,5004:\\r\\n': self.get_sensor_name,
            '%R1Q,9027:(-?[0-9]*\.?[0-9]+),(-?[0-9]*\.?[0-9]+),2,1,0\\r\\n':
                self.set_direction,
            '%R1Q,2008:1,1\\r\\n': self.measure_distance,
            '%R1Q,2167:5000,1\\r\\n': self.do_complete_measurement
        }

    def do_complete_measurement(self, request):
        return_code = '0'
        hz = '{:0.15f}'.format(random.uniform(0, 2 * math.pi))
        v = '{:0.15f}'.format(random.uniform(1, 2))
        acc_angle = '{:0.15f}'.format(random.uniform(-1, 1) * 10e-6)
        c = '{:0.15f}'.format(random.uniform(-1, 1) * 10e-5)
        l = '{:0.15f}'.format(random.uniform(-1, 1) * 10e-5)
        acc_incl = '{:0.15f}'.format(random.uniform(-1, 1) * 10e-6)
        slope_dist = '{:0.15f}'.format(random.uniform(1, 2000))
        dist_time = '{:8.0f}'.format(random.uniform(4, 5) * 10e8)

        response = '%R1P,0,0:{},{},{},{},{},{},{},{},{}\r\n'.format(
            return_code,
            hz,
            v,
            acc_angle,
            c,
            l,
            acc_incl,
            slope_dist,
            dist_time)

        return response

    def get_sensor_id(self, request):
        return_code = '0'
        response = '%R1P,0,0:{},999999\r\n'.format(return_code)

        return response

    def get_sensor_name(self, request):
        return_code = '0'
        response = '%R1P,0,0:{},"TM30 0.5"\r\n'.format(return_code)

        return response

    def measure_distance(self, request):
        return_code = '0'
        response = '%R1P,0,0:{}\r\n'.format(return_code)

        return response

    def set_direction(self, request):
        return_code = '0'
        response = '%R1P,0,0:{}\r\n'.format(return_code)

        return response


class VirtualDTM(VirtualSensor):
    """
    VirtualDTM simulates an STS DTM meteorological sensor.
    """

    def __init__(self, name, type, managers):
        VirtualSensor.__init__(self, name, type, managers)

        self.patterns = {
            'A\\r': self.power_on,
            'CMDT 1\\r': self.set_command_set,
            'SAVE\\r': self.save,
            'PRES \?\\r': self.get_pressure,
            'TEMP \?\\r': self.get_temperature
        }

    def get_pressure(self, request):
        high = 1150
        low = 980

        return '+{:06.1f}\r'.format(random.uniform(low, high))

    def get_temperature(self, request):
        high = 40
        low = -20

        t = random.uniform(low, high)

        if t < 0:
            return '{:07.1f}\r'.format(t)
        else:
            return '+{:06.1f}\r'.format(t)

    def power_on(self, request):
        return '#\r'

    def save(self, request):
        return '*\r'

    def set_command_set(self, request):
        return '*\r'


class VirtualIndicatorOne(VirtualSensor):
    """
    VirtualIndicatorOne simulates a Sylvac S_Dial One digital
    indicator/extensometer.
    """

    def __init__(self, name, type, managers):
        VirtualSensor.__init__(self, name, type, managers)

        self._current_value = 0.0
        self.patterns = {
            '\?\r': self.get_distance
        }

    def get_distance(self, request):
        x = (1.0 + math.sin(self._current_value)) * 12.5
        self._current_value += 0.25

        return '{:7.3f}\r'.format(x)
