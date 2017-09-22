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

"""Module for BSD-specific features, which are not available on other operating
systems."""

__author__ = 'Philipp Engel'
__copyright__ = 'Copyright (c) 2017 Hochschule Neubrandenburg'
__license__ = 'EUPL'

import queue
import shlex
import subprocess
import time
import threading

from enum import Enum
from typing import *

from core.manager import Manager
from module.prototype import Prototype


class Unix(Enum):

    FREEBSD = 0
    NETBSD = 1
    OPENBSD = 2


class GpioController(Prototype):

    """GpioController sets single pins of the General Purpose Input Output
    (GPIO) interface of a Raspberry Pi single-board computer running FreeBSD or
    NetBSD. This module does not work on Linux. Support for OpenBSD may be added
    in future."""

    def __init__(self, module_name: str, module_type: str, manager: Manager):
        super().__init__(module_name, module_type, manager)
        config = self.get_config(self._name)

        self._default_state = config.get('defaultState')
        self._duration = config.get('duration')
        self._pin = config.get('pin')

        os = str(config.get('os'))

        if os.lower() == 'freebsd':
            self._os = Unix.FREEBSD
        elif os.lower() == 'netbsd':
            self._os = Unix.NETBSD
        else:
            raise ValueError('Operating system must be either '
                             '"FreeBSD" or "NetBSD"')

        self._cmd_freebsd = 'gpioctl -f /dev/gpioc0 {} {}'
        self._cmd_netbsd = 'gpioctl gpio0 {} {}'

        self._queue = queue.Queue(-1)
        self._thread = None

        self.add_handler('gpio', self.handle_gpio)
        manager.schema_manager.add_schema('gpio', 'gpio.json')

    def _communicate(self, cmd: str) -> Tuple[str, str]:
        """Communicates with the operating system using `subprocess`.

        Args:
            cmd: The command to execute.

        Returns:
            The stdout and stderr of the process.
        """
        args = shlex.split(cmd)
        process = subprocess.Popen(args,
                                   stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()

        return stdout.decode('utf-8'), stderr.decode('utf-8')

    def _set_pin(self, pin: str, value: int) -> None:
        """Sets given pin to value.

        Args:
            pin: The pin name or number.
            value: The value to set the pin to (e.g., 0 or 1).
        """
        if self._os == Unix.FREEBSD:
            cmd = self._cmd_freebsd.format(pin, value)
        elif self._os == Unix.NETBSD:
            cmd = self._cmd_netbsd.format(pin, value)

        out, err = self._communicate(cmd)

        if err and len(err) > 0:
            self.logger.error('Setting pin "{}" to "{}" failed: {}'
                              .format(pin, value, err))
        else:
            self.logger.info('Set pin "{}" to "{}"'.format(pin, value))

    def handle_gpio(self,
                    header: Dict[str, Any],
                    payload: Dict[str, Any]) -> None:
        """Puts message payload in the queue.

        Args:
            header: The message header.
            payload: The message payload.
        """
        self._queue.put(payload)

    def run(self) -> None:
        """Waits for new messages and sets GPIO pin to high or low."""
        while self.is_running:
            message = self._queue.get()      # Blocking I/O.
            value = message.get('value', self._default_state)

            if value in ["0", "1"]:
                self._set_pin(self._pin, value)

            time.sleep(self._duration)

            self._set_pin(self._pin, self._default_state)

    def start(self) -> None:
        if self._is_running:
            return

        super().start()

        self._thread = threading.Thread(target=self.run)
        self._thread.daemon = True
        self._thread.start()
