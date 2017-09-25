#!/usr/bin/env python3.6
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

"""Module for Linux-specific features, which are not available on other
operating systems."""

__author__ = 'Philipp Engel'
__copyright__ = 'Copyright (c) 2017 Hochschule Neubrandenburg'
__license__ = 'EUPL'

import arrow
import logging
import time
import threading

try:
    import RPi.GPIO as GPIO
except ImportError:
    logging.getLogger().critical('Importing Python module "RPi.GPIO" failed')

from core.observation import Observation
from core.manager import Manager
from module.prototype import Prototype


class InterruptCounter(Prototype):
    """
    Counts GPIO interrupts on a single pin of a Raspberry Pi single-board
    computer. Works on Linux only.

    Configuration:
        bounceTime: Bounce time in ms.
        countTime: Observation time in s.
        pin: GPIO pin number of the Raspberry Pi.
        receiver: Name of the receiving module.
        sensorName: Name of the connected sensor.
    """

    def __init__(self, module_name: str, module_type: str, manager: Manager):
        super().__init__(module_name, module_type, manager)
        config = self.get_config(self._name)

        self._pin = config.get('pin')
        self._bounce_time = config.get('bounceTime')
        self._count_time = config.get('countTime')
        self._receiver = config.get('receiver')
        self._sensor_name = config.get('sensorName')

        self._counter = 0
        self._thread = None
        self._lock = threading.Lock()

        self.init_gpio()

    def __del__(self):
        GPIO.cleanup()

    def init_gpio(self) -> None:
        """Initializes the GPIO interface."""
        # Set SoC as reference.
        GPIO.setmode(GPIO.BCM)
        # Set pin as input and activate pull-down resistor.
        GPIO.setup(self._pin,
                   GPIO.IN,
                   pull_up_down=GPIO.PUD_DOWN)
        # Add interrupt event.
        GPIO.add_event_detect(self._pin,
                              GPIO.RISING,
                              callback=self._interrupt,
                              bouncetime=self._bounce_time)

    def _interrupt(self) -> None:
        """Catches an interrupt and increases the counter."""
        self._lock.acquire()

        try:
            self._counter += 1
            self.logger.debug('Counted interrupt {} on GPIO pin {}'
                              .format(self._counter, self._pin))
        finally:
            self._lock.release()

    def run(self) -> None:
        """The counter loop. Creates a new observation at the defined
        interval."""
        t1 = time.time()
        t2 = t1

        while self._is_running:
            dt = t2 - t1
            time.sleep(self._count_time - dt)
            t1 = time.time()
            counter = 0

            self._lock.acquire()

            try:
                counter = self._counter
                self._counter = 0
            finally:
                self._lock.release()

            self._fire(counter)
            t2 = time.time()

    def _fire(self, c: int) -> None:
        """Creates a new observation with the given counter value."""
        obs = Observation()
        gpio = 'gpio{}'.format(self._pin)

        response_sets = {
            gpio: Observation.create_response_set('int', 'none', c)
        }

        obs.set('enabled', False)
        obs.set('name', 'interruptCount')
        obs.set('nextReceiver', 0)
        obs.set('node', self._node_manager.node.id)
        obs.set('onetime', False)
        obs.set('portName', 'GPIO{}'.format(self._pin))
        obs.set('project', self._project_manager.project.id)
        obs.set('receivers', [self._receiver])
        obs.set('responseSets', response_sets)
        obs.set('sensorName', self._sensor_name)
        obs.set('sensorType', 'gpio')
        obs.set('sleepTime', 0.0)
        obs.set('target', gpio)
        obs.set('timeStamp', str(arrow.utcnow()))

        self.publish_observation(obs)

    def start(self) -> None:
        if self._is_running:
            return

        super().start()

        # Run the method `run()` within a thread.
        self._thread = threading.Thread(target=self.run)
        self._thread.daemon = True
        self._thread.start()
