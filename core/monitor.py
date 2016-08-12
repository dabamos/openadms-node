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
import queue
import threading
import time

from core import manager
from core import sensor

"""Main monitoring module."""

logger = logging.getLogger('openadms')


class Monitor(object):

    """
    Monitor is used to manage the monitoring process.
    """

    def __init__(self, config_file):
        self._config_manager = None
        self._module_manager = None
        self._sensor_manager = None

        self._config_manager = manager.ConfigurationManager(config_file)
        self._sensor_manager = manager.SensorManager(self._config_manager)
        self._module_manager = manager.ModuleManager(self._config_manager,
                                                     self._sensor_manager)

    @property
    def config_manager(self):
        return self._config_manager

    @property
    def module_manager(self):
        return self._module_manager

    @property
    def sensor_manager(self):
        return self._sensor_manager
