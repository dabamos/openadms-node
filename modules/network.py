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

import itertools
import logging
import socket

from datetime import datetime

from modules import prototype

"""Module for sending observation data over a UDP socket."""

logger = logging.getLogger('netadms')

UDP_TARGET = '127.0.0.1'
UDP_PORT = 7000

class UDPSend(prototype.Prototype):

    """
    Sends observation data over a UDP socket. For testing only.
    """

    def __init__(self, name, config_manager):
        prototype.Prototype.__init__(self, name, config_manager)

        self._config_manager = config_manager
        self._sock_target = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    def action(self, obs_data):
        """Sends comma separated values over a UDP socket."""
        dt = datetime.fromtimestamp(obs_data.get('TimeStamp'))
        line = dt.strftime('%Y-%m-%dT%H:%M:%S.%f')

        values = obs_data.get('Values')
        units = obs_data.get('Units')

        # Add values and units to the line.
        for v, u in itertools.zip_longest(values, units):
            line += ',' + format(v)
            line += ',' + format(u)

        line += '\n'

        self._sock_target.sendto(bytes(line, 'utf-8'),
                                 (UDP_TARGET, UDP_PORT))

        logger.info('Sent observation data from {} to {} on port {} (UDP)'.
            format(obs_data.get('InterfaceName'), UDP_TARGET, UDP_PORT))

        return obs_data

    def destroy(self, *args):
        self._sock_target.close()
