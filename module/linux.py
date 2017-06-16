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

"""Module for data processing (pre-processing, atmospheric corrections,
transformations, and so on)."""

__author__ = 'Philipp Engel'
__copyright__ = 'Copyright (c) 2017 Hochschule Neubrandenburg'
__license__ = 'EUPL'

import time

import RPi.GPIO as GPIO

from core.observation import Observation
from module.prototype import Prototype


class InterruptCounter(Prototype):
    """
    Counts GPIO interrupts of a Raspberry Pi single-board computer.
    """

    def __init__(self, name, type, manager):
        Prototype.__init__(self, name, type, manager)
        config = self._config_manager.get(self._name)

        self._pin = config.get('pin')
        self._bounce_time = config.get('bounceTime')
        self._count = 0

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

    def process_observation(self, obs):

    def _interrupt(chan):
        self._count += 1



