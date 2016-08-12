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

    def __init__(self, name, config_manager, sensor_manager):
        prototype.Prototype.__init__(self, name, config_manager,
                                     sensor_manager)

        self._serial = None         # Pyserial object.
        self._serial_port_config = None
        self._max_attempts = 3

    def __del__(self):
        #if self._serial is not None:
        #    self.close()
        pass

    def action(self, obs):
        if not self._serial:
            self._open()

        response = ''

        # Add the name of this serial port to the observation.
        obs.set('PortName', self.name)

        # Send the request of the observation to the attached sensor.
        logger.info('Sending observation "{}" to sensor "{}" on port '
                    '"{}"'.format(obs.get('Name'),
                                  obs.get('SensorName'),
                                  self.name))
        if self._serial == None:
            logger.error('Could not write to port {} ({})'
                         .format(self.name, self._serial_port_config.port))
            return

        for attempt in range(self._max_attempts):
            if attempt > 0:
                logger.info('Attempt {} of {} ...'.format(attempt + 1,
                                                          self._max_attempts))

            # Write to the serial port.
            self._write(obs.get('Request'))

            # Wait some time to let the sensor do its sensoring stuff.
            time.sleep(obs.get('AwaitTime'))

            # Get the response of the sensor.
            response = self._read(obs.get('ResponseDelimiter'))

            if response != '':
                logger.debug('Received response "{}" from sensor "{}" on '
                             'port "{}"'.format(self._sanitize(response),
                                                obs.get('SensorName'),
                                                self.name))
                break

            # Try next attempt if response is empty.
            logger.error('No response from sensor "{}" on port "{}"'
                         .format(obs.get("SensorName"), self.name))

        # Add a timestamp to the observation.
        obs.set('TimeStamp', time.time())

        # Add the raw response of the sensor to the observation set.
        obs.set('Response', response)

        self.publish(obs)

    def close(self):
        logger.info('Closing port {} ({})'
                    .format(self.name, self._serial_port_config.port))
        self._serial.close()

    def _get_port_config(self):
        p = self._config_manager.config.get('Ports') \
                                       .get('Serial') \
                                       .get(self.name)

        if not p:
            logger.debug('No port {} in configuration'.format(self.name))

        return SerialPortConfiguration(
            port=p.get('Port'),
            baudrate=p.get('BaudRate'),
            bytesize=p.get('ByteSize'),
            stopbits=p.get('StopBits'),
            parity=p.get('Parity'),
            timeout=p.get('Timeout'),
            xonxoff=p.get('SoftwareFlowControl'),
            rtscts=p.get('HardwareFlowControl'))

    def _open(self):
        """Opens a serial port."""
        if not self._serial_port_config:
            self._serial_port_config = self._get_port_config()

        logger.info('Opening port {} ({}) ...'
                    .format(self.name, self._serial_port_config.port))

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
            logger.error('Permission denied for port {} ({})'
                         .format(self.name, self._serial_port_config.port))

    def _read(self, eol, timeout=10.0):
        """Reads from serial port."""
        response = ''
        start_time = time.time()

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
                             .format(self.name, self._serial_port_config.port))
                break

            if time.time() - start_time > timeout:
                logger.warning('Timeout on port "{}" after {} s'
                               .format(self.name, timeout))
                break

        return response

    def _sanitize(self, s):
        """Converts some non-printable characters of a given string."""
        return s.replace('\n', '\\n') \
                .replace('\r', '\\r') \
                .replace('\t', '\\t') \
                .strip()

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
