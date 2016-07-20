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
import serial
import time

from modules import prototype

"""Module for sensor communication."""

logger = logging.getLogger('openadms')


class SerialPort(prototype.Prototype):
    """
    I/O on serial port.
    """

    def __init__(self, name, config_manager):
        prototype.Prototype.__init__(self, name, config_manager)

        self._serial = None         # Pyserial object.
        self._serial_port_config = None

    def action(self, obs_data):
        if not self._serial:
            self._open()

        # Add the name of this serial port to the observation data.
        obs_data.set('PortName', self._name)

        # Send the request of the observation data to the attached sensor.
        logger.info('Sending observation "{}" ("{}") to sensor "{}" on port '
                    '"{}"'.format(obs_data.get('Name'),
                                  self._sanitize(obs_data.get('Request')),
                                  obs_data.get('SensorName'),
                                  self._name))
        if self._serial == None:
            logger.error('Could not write to port {} ({})'
                         .format(self._name, self._serial_port_config.port))
            return

        self._write(obs_data.get('Request'))

        # Wait some time to let the sensor do its sensoring stuff.
        time.sleep(obs_data.get('AwaitTime'))
        # Get the response of the sensor.
        response = self._read(obs_data.get('ResponseDelimiter'))

        if response == '':
            logger.warning('No response from sensor "{}" on port "{}"'
                           .format(obs_data.get("SensorName"), self._name))
            return

        # Add a timestamp to the observation data.
        obs_data.set('TimeStamp', time.time())

        logger.info('Received "{}" from sensor "{}" on port "{}"'
                    .format(self._sanitize(response),
                            obs_data.get('SensorName'),
                            self._name))

        # Add the raw response of the sensor to the observation data set.
        obs_data.set('Response', response)

        return obs_data

    def close(self):
        logger.info('Closing port {} ({})'
                    .format(self._serial_port_config.name,
                            self._serial_port_config.port))
        self._serial.close()

    def destroy(self, *args):
        self.close()

    def _get_port_config(self):
        try:
            p = self._config_manager.config['Ports']['Serial'][self._name]
        except KeyError:
            logger.debug('No port {} in configuration'.format(self._name))
            return

        return SerialPortConfiguration(
            port=p['Port'],
            baudrate=p['BaudRate'],
            bytesize=p['ByteSize'],
            stopbits=p['StopBits'],
            parity=p['Parity'],
            timeout=p['Timeout'],
            xonxoff=p['SoftwareFlowControl'],
            rtscts=p['HardwareFlowControl'])

    def _open(self):
        """Opens a serial port."""
        if self._name is None:
            logger.error('No port name set')
            return

        if self._serial_port_config is None:
            self._serial_port_config = self._get_port_config()

        logger.info('Opening port {} ({}) ...'
            .format(self._name, self._serial_port_config.port))

        try:
            self._serial = serial.Serial(
                port=self._serial_port_config.port,            # Port (e.g., "/dev/tty0").
                baudrate=self._serial_port_config.baudrate,    # Baudrate (e.g., "9600").
                timeout=self._serial_port_config.timeout,      # Timeout in seconds.
                bytesize=self._serial_port_config.bytesize,    # Data bytes (e.g., "8").
                parity=self._serial_port_config.parity,        # Parity (e.g., "none")
                stopbits=self._serial_port_config.stopbits,    # Stop bits (e.g., "1").
                xonxoff=self._serial_port_config.xonxoff,      # Software flow control.
                rtscts=self._serial_port_config.rtscts)        # Hardware flow control.
        except serial.serialutil.SerialException:
            logger.error('Permission denied for port {} ({})'
                         .format(self._name, self._serial_port_config.port))

    def _read(self, eol):
        """Reads from serial port."""
        response = ''

        # Read from serial port until delimiter occurs.
        while True:
            try:
                rxd = self._serial.read(1).decode()
                response += rxd

                # Did we get an end of line (e.g., '\r' or '\n')?
                i = len(eol)

                if len(response) >= len(eol) and response[-i:] == eol:
                    break
            except UnicodeDecodeError:
                logger.error('No sensor on port "{}" ({})'
                            .format(self._name, self._serial_port_config.port))
                break

        return response

    def _sanitize(self, s):
        """Converts some non-printable characters of a given string."""
        san = s.replace('\n', '\\n')
        san = san.replace('\r', '\\r')
        san = san.replace('\t', '\\t')

        return san.strip()

    def _write(self, data):
        """Sends command to sensor."""
        self._serial.write(data.encode())


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
