#!/usr/bin/env python3.6

"""             ,        ,         
               /(        )`        
               \ \___   / |        
               /- _  `-/  '        
              (/\/ \ \   /\        
              / /   | `    \       
              O O   ) /    |       
              `-^--'`<     '       
             (_.)  _  )   /        
              `.___/`    /         
                `-----' /          
   <----.     __ / __   \          
   <----|====O)))==) \) /====|      
   <----'    `--' `.__,' \         
                |        |         
                 \       /       /\
            ______( (_  / \______/ 
          ,'  ,-----'   |          
          `--{__________)
          
Module for BSD-specific features, which are not available on other operating
systems.
"""

__author__ = 'Philipp Engel'
__copyright__ = 'Copyright (c) 2017 Hochschule Neubrandenburg'
__license__ = 'BSD (2-Clause)'

import queue
import shlex
import subprocess
import time
import threading

from enum import Enum
from typing import *

from core.manager import Manager
from core.system import System
from module.prototype import Prototype


class Unix(Enum):
    """
    Type of BSD Unix derivate.
    """

    NONE = 0
    FREEBSD = 1
    NETBSD = 2
    OPENBSD = 3


class GpioController(Prototype):
    """
    GpioController sets single pins of the General Purpose Input Output
    (GPIO) interface of a Raspberry Pi single-board computer running FreeBSD,
    NetBSD, or OpenBSD. This module does not work on Linux.
    """

    def __init__(self, module_name: str, module_type: str, manager: Manager):
        super().__init__(module_name, module_type, manager)
        config = self.get_config(self._name)

        self._default_state = config.get('defaultState')
        self._duration = config.get('duration')
        self._pin = config.get('pin')

        self._os = {
            'FreeBSD': Unix.FREEBSD,
            'NetBSD': Unix.NETBSD,
            'OpenBSD': Unix.OPENBSD
        }.get(System.get_os_name(), Unix.NONE)

        if self._os == Unix.NONE:
            raise ValueError('Operating system is not supported')

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

    def _get_command(self, os: Unix) -> Union[str, None]:
        """Returns derivate-specific command to set a single pin of the GPIO
        interface.

        Args:
            os: The BSD unix derivate.

        Returns:
            Command to access the GPIO interface on BSD.
        """
        cmd = {
            Unix.FREEBSD: 'gpioctl -f /dev/gpioc0 {} {}',
            Unix.NETBSD: 'gpioctl gpio0 {} {}',
            Unix.OPENBSD: 'gpioctl gpio0 {} {}'
        }.get(os, None)

        return cmd

    def _set_pin(self, pin: str, value: int) -> None:
        """Sets given pin to value.

        Args:
            pin: The pin name or number.
            value: The value to set the pin to (e.g., 0 or 1).
        """
        cmd = self._get_command(self._os).format(pin, value)
        out, err = self._communicate(cmd)

        if err and len(err) > 0:
            self.logger.error('Setting GPIO pin "{}" to "{}" failed: {}'
                              .format(pin, value, err))
        else:
            self.logger.verbose('Set GPIO pin "{}" to "{}"'.format(pin, value))

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

            if value in [0, 1, "0", "1"]:
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
