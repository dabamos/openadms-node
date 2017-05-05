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

import copy
import re
import socket
import threading
import time

import serial

from enum import Enum

from core.observation import Observation
from core.util import System
from module.prototype import Prototype

"""Module for sensor communication."""


class BluetoothPort(Prototype):
    """
    BluetoothPort is used for RFCOMM serial communication. It initiates a
    socket connection to a sensor by using the native Bluetooth support of
    Python 3.3. At the moment, the class is not very useful and needs further
    testing.
    """

    def __init__(self, name, type, manager):
        Prototype.__init__(self, name, type, manager)
        self._config = self._config_manager.get('ports')\
                                           .get('bluetooth')\
                                           .get(self._name)
        self._port = self._config.get('port')
        self._server_mac_address = None
        self._sock = None

        valid_mac = self.get_mac_address(self._config.get('serverMacAddress'))

        if not valid_mac:
            self.logger.error('Invalid MAC address "{}"'
                              .format(self._config.get('serverMacAddress')))
        else:
            self._server_mac_address = valid_mac

    def __del__(self):
        self.close()

    def close(self):
        if self._sock:
            self.logger.info('Closing port "{}" ...'.format(self._port))
            self._sock.close()

    def get_mac_address(self, s):
        if re.match(r'^[a-fA-F0-9]{2}(?::[a-fA-F0-9]{2}){5}$', s):
            return s
        elif re.match(r'^[a-fA-F0-9]{12}$', s):
            l = re.findall('..', s)
            return '{}:{}:{}:{}:{}:{}'.format(*l)
        else:
            return

    def process_observation(self, obs):
        if System.is_windows():
            self.logger.critical('Operating system not supported (no '
                                 'socket.AF_BLUETOOTH on Microsoft Windows)')
            return

        if not self._sock:
            # Open socket connection.
            if not self._open():
                return

        # Add the name of this Bluetooth port to the observation.
        obs.set('portName', self.name)

        requests_order = obs.get('requestsOrder', [])
        request_sets = obs.get('requestSets')

        if len(requests_order) == 0:
            self.logger.info('No requests order defined in observation "{}" '
                             'with ID "{}"'.format(obs.get('name'),
                                                   obs.get('id')))

        # Send requests one by one to the sensor.
        for request_name in requests_order:
            request_set = request_sets.get(request_name)

            if not request_set:
                self.logger.error('Request set "{}" not found in observation '
                                  '"{}" with ID "{}"'.format(request_name,
                                                             obs.get('name'),
                                                             obs.get('id')))
                return

            # The response of the sensor.
            response = ''
            response_delimiter = request_set.get('responseDelimiter')

            # Data of the request set.
            request = request_set.get('request')
            sleep_time = request_set.get('sleepTime')
            timeout = request_set.get('timeout')

            # Send the request of the observation to the attached sensor.
            self.logger.info('Sending request "{}" of observation "{}" to '
                             'sensor "{}"'.format(request_name,
                                                  obs.get('name'),
                                                  obs.get('sensorName')))
            # Write to the Bluetooth port.
            self._send(request)

            # Get the response of the sensor.
            response = self._receive(response_delimiter, timeout)

            self.logger.debug('Received response "{}" for request "{}" '
                              'of observation "{}" from sensor "{}"'
                              .format(self._sanitize(response),
                                      request_name,
                                      obs.get('name'),
                                      obs.get('sensorName')))
            # Add the raw response of the sensor to the observation set.
            request_set['response'] = response

            # Add the timestamp to the observation.
            obs.set('timeStamp', time.time())

            # Sleep until the next request.
            time.sleep(sleep_time)

        return obs

    def _open(self):
        if not self._server_mac_address:
            self.logger.error('MAC address of server not set')
            return False

        try:
            self._sock = socket.socket(socket.AF_BLUETOOTH,
                                       socket.SOCK_STREAM,
                                       socket.BTPROTO_RFCOMM)
            self._sock.connect((self._server_mac_address, self._port))
        except OSError as e:
            self.logger.error(e)
        except TimeoutError as e:
            self.logger.error(e)

    def _receive(self, eol, timeout=30.0):
        """Reads from Bluetooth connection."""
        response = ''
        start_time = time.time()

        # Read from Bluetooth port until delimiter occurs.
        while True:
            try:
                rxd = self._sock.recv(1).decode()
                response += rxd

                # Did we get an end of line (e.g., '\r' or '\n')?
                i = len(eol)

                if len(response) >= len(eol) and response[-i:] == eol:
                    break
            except UnicodeDecodeError:
                self.logger.error('No sensor on port "{}"'
                                  .format(self._port))
                break

            if time.time() - start_time > timeout:
                self.logger.warning('Timeout on port "{}" after {} s'
                                    .format(self._port,
                                            timeout))
                break

        return response

    def _send(self, data):
        """Sends command to sensor."""
        self._sock.send(bytes(data, 'UTF-8'))


class ConnectionMode(Enum):
    """
    Enumeration of serial port connection mode.
    """

    ACTIVE = 0
    PASSIVE = 1


class SerialPort(Prototype):
    """
    SerialPort does I/O on a given serial port. The port can be used in either
    active or passive mode. In active mode, the communication with the sensor is
    based on request/response. In passive mode, the port just listens for
    incoming data.
    """

    def __init__(self, name, type, manager):
        Prototype.__init__(self, name, type, manager)
        self._config = self._config_manager.config.get('ports')\
                                                  .get('serial')\
                                                  .get(self.name)
        if self._config.get('mode') == 'passive':
            self._mode = ConnectionMode.PASSIVE
            self._obs_template = None
        else:
            self._mode = ConnectionMode.ACTIVE

        self._thread = None     # Thread for passive mode.
        self._serial = None     # Pyserial object.
        self._serial_port_config = None
        self._max_attempts = 1  # TODO: Move to configuration file.

    def __del__(self):
        # self.close()
        pass

    def close(self):
        if self._serial:
            self.logger.info('Closing port "{}" ...'
                             .format(self._serial_port_config.port))
            self._serial.close()

    def is_passive_mode(self):
        if self._mode == ConnectionMode.PASSIVE:
            return True
        else:
            return False

    def process_observation(self, obs):
        if self.is_passive_mode():
            # Set observation template for passive mode.
            self._obs_template = obs
            return

        if not self._serial:
            self._create()

        if self._serial is None:
            self.logger.error('Could not access port "{}"'
                              .format(self._serial_port_config.port))
            return

        if not self._serial.is_open:
            self.logger.info('Re-opening port "{}" ...'
                             .format(self._serial_port_config.port))
            self._serial.open()
            self._serial.reset_output_buffer()
            self._serial.reset_input_buffer()

        # Add the name of this serial port to the observation.
        obs.set('portName', self.name)

        requests_order = obs.get('requestsOrder', [])
        request_sets = obs.get('requestSets')

        if len(requests_order) == 0:
            self.logger.info('No requests order defined in observation "{}" '
                             'with ID "{}"'.format(obs.get('name'),
                                                   obs.get('id')))

        # Send requests one by one to the sensor.
        for request_name in requests_order:
            request_set = request_sets.get(request_name)

            if not request_set:
                self.logger.error('Request set "{}" not found in observation '
                                  '"{}" with ID "{}"'.format(request_name,
                                                             obs.get('name'),
                                                             obs.get('id')))
                return

            # The response of the sensor.
            response = ''
            response_delimiter = request_set.get('responseDelimiter')

            # Data of the request set.
            request = request_set.get('request')
            sleep_time = request_set.get('sleepTime')
            timeout = request_set.get('timeout')

            # Send the request of the observation to the attached sensor.
            self.logger.info('Sending request "{}" of observation "{}" to '
                             'sensor "{}"'.format(request_name,
                                                  obs.get('name'),
                                                  obs.get('sensorName')))

            for attempt in range(self._max_attempts):
                if attempt > 0:
                    self.logger.info('Attempt {} of {} ...'
                                     .format(attempt + 1, self._max_attempts))
                    time.sleep(1)

                # Write to the serial port.
                self._write(request)

                # Get the response of the sensor.
                response = self._read(eol=response_delimiter,
                                      length=0,
                                      timeout=timeout)

                self._serial.reset_output_buffer()
                self._serial.reset_input_buffer()

                if response != '':
                    self.logger.debug('Received response "{}" for request "{}" '
                                      'of observation "{}" from sensor "{}"'
                                      .format(self._sanitize(response),
                                              request_name,
                                              obs.get('name'),
                                              obs.get('sensorName')))
                    break

                # Try next attempt if response is empty.
                self.logger.warning('No response from sensor "{}" for '
                                    'observation "{}" with ID "{}"'
                                    .format(obs.get('sensorName'),
                                            obs.get('name'),
                                            obs.get('id')))

            # Add the raw response of the sensor to the observation set.
            request_set['response'] = response

            # Add the timestamp to the observation.
            obs.set('timeStamp', time.time())

            # Sleep until the next request.
            time.sleep(sleep_time)

        return obs

    def run(self):
        """Threaded method for passive mode. Reads incoming data from serial
        port. Used for sensors which start streaming data without prior
        request."""
        if self.is_active_mode() or self._obs_template is None:
            self.logger.warning('Module not in passive mode')
            return

        while self._is_running:
            if not self._serial:
                self._create()

            if self._serial is None:
                self.logger.error('Could not access port "{}"'
                                  .format(self._serial_port_config.port))
                return

            if not self._serial.is_open:
                self.logger.info('Re-opening port "{}" ...'
                                 .format(self._serial_port_config.port))
                self._serial.open()
                self._serial.reset_output_buffer()
                self._serial.reset_input_buffer()

            obs = copy.deepcopy(self._obs_template)
            obs.set('portName', self.name)

            request_set = obs.get('requestSets').get('default')
            timeout = request_set.get('timeout')
            response_delimiter = request_set.get('responseDelimiter')
            length = request_set.get('responseLength')

            response = self._read(eol=response_delimiter,
                                  length=length,
                                  timeout=timeout)

            if response != '':
                request_set['response'] = response
                obs.set('timeStamp', time.time())
                self._publish_observation(obs)

    def start(self):
        if self._is_running:
            return

        self.logger.debug('Starting worker "{}" ...'.format(self._name))
        self._is_running = True

        if self.is_passive_mode():
            self._thread = threading.Thread(target=self.run)
            self._thread.daemon = True
            self._thread.start()

    def _get_port_config(self):
        if not self._config:
            self.logger.debug('No port "{}" defined in configuration'
                              .format(self.name))

        return SerialPortConfiguration(
            port=self._config.get('port'),
            baudrate=self._config.get('baudRate'),
            bytesize=self._config.get('byteSize'),
            stopbits=self._config.get('stopBits'),
            parity=self._config.get('parity'),
            timeout=self._config.get('timeout'),
            xonxoff=self._config.get('softwareFlowControl'),
            rtscts=self._config.get('hardwareFlowControl'))

    def _create(self):
        """Opens a serial port."""
        if not self._serial_port_config:
            self._serial_port_config = self._get_port_config()

        self.logger.info('Opening port "{}" ...'
                         .format(self._serial_port_config.port))

        try:
            self._serial = serial.Serial(
                port=self._serial_port_config.port,
                baudrate=self._serial_port_config.baudrate,
                timeout=self._serial_port_config.timeout,
                bytesize=self._serial_port_config.bytesize,
                parity=self._serial_port_config.parity,
                stopbits=self._serial_port_config.stopbits,
                xonxoff=self._serial_port_config.xonxoff,
                rtscts=self._serial_port_config.rtscts)
        except serial.serialutil.SerialException:
            self.logger.error('Permission denied for port "{}"'
                              .format(self._serial_port_config.port))

    def _read(self, eol=None, length=0, timeout=30.0):
        """Reads from serial port."""
        response = ''
        start_time = time.time()
        c = 0                       # Character index.

        # Read from serial port until delimiter occurs.
        while True:
            try:
                rxd = self._serial.read(1).decode()
                response += rxd

                if length and length > 0:
                    c += 1

                    if c == length - 1:
                        break

                if eol:
                    # Did we get an end of line (e.g., '\r' or '\n')?
                    i = len(eol)

                    if len(response) >= len(eol) and response[-i:] == eol:
                        break
            except UnicodeDecodeError:
                self.logger.error('No sensor on port "{}"'
                                  .format(self._serial_port_config.port))
                break

            if time.time() - start_time > timeout:
                self.logger.warning('Timeout on port "{}" after {} s'
                                    .format(self._serial_port_config.port,
                                            timeout))
                break

        return response

    def _sanitize(self, s):
        """Converts some non-printable characters of a given string."""
        return s.replace('\n', '\\n')\
                .replace('\r', '\\r')\
                .replace('\t', '\\t')\
                .strip()

    def _write(self, data):
        """Sends command to sensor."""
        self._serial.write(data.encode())

    def is_active_mode(self):
        if self._mode == ConnectionMode.ACTIVE:
            return True
        else:
            return False


class SerialPortConfiguration(object):
    """
    SerialPortConfiguration saves a serial port configration.
    """

    def __init__(self, port, baudrate, bytesize, stopbits, parity, timeout,
                 xonxoff, rtscts):
        """Converts data from JSON style to serial.Serial style."""
        self._port = port
        self._baudrate = baudrate
        self._bytesize = {
            5: serial.FIVEBITS,
            6: serial.SIXBITS,
            7: serial.SEVENBITS,
            8: serial.EIGHTBITS
        }[bytesize]
        self._stopbits = {
            1: serial.STOPBITS_ONE,
            1.5: serial.STOPBITS_ONE_POINT_FIVE,
            2: serial.STOPBITS_TWO
        }[stopbits]
        self._parity = {
            'none': serial.PARITY_NONE,
            'even': serial.PARITY_EVEN,
            'odd': serial.PARITY_ODD,
            'mark': serial.PARITY_MARK,
            'space': serial.PARITY_SPACE
        }[parity]
        self._timeout = timeout
        self._xonxoff = xonxoff
        self._rtscts = rtscts

    @property
    def port(self):
        return self._port

    @property
    def baudrate(self):
        return self._baudrate

    @property
    def bytesize(self):
        return self._bytesize

    @property
    def stopbits(self):
        return self._stopbits

    @property
    def parity(self):
        return self._parity

    @property
    def timeout(self):
        return self._timeout

    @property
    def xonxoff(self):
        return self._xonxoff

    @property
    def rtscts(self):
        return self._rtscts
