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

"""Module for testing the monitoring system."""

__author__ = 'Philipp Engel'
__copyright__ = 'Copyright (c) 2017 Hochschule Neubrandenburg'
__license__ = 'EUPL'

import threading
import time

from core.manager import Manager
from module.prototype import Prototype


class ErrorGenerator(Prototype):
    """
    ErrorGenerates creates WARNING, ERROR, or CRITICAL log messages in a given
    interval for testing.
    """

    def __init__(self, module_name: str, module_type: str, manager: Manager):
        """
        Args:
            module_name: The name of the module.
            module_type: The type of the module.
            manager: The manager objects.
        """
        super().__init__(module_name, module_type, manager)
        config = self.get_config(self._name)

        self._is_warning_enabled = config.get('warning', False)
        self._is_error_enabled = config.get('error', False)
        self._is_critical_enabled = config.get('critical', False)
        self._interval = config.get('interval', 10.0)

        self._warning_count = 1
        self._error_count = 1
        self._critical_count = 1

        self._thread = None

    def run(self) -> None:
        """Generates log messages in the set interval."""
        while self.is_running:
            time.sleep(self._interval)

            if self._is_warning_enabled:
                self.logger.warning('--- WARNING #{} ---'
                                    .format(self._warning_count))
                self._warning_count += 1

            if self._is_error_enabled:
                self.logger.error('--- ERROR #{} ---'
                                  .format(self._error_count))
                self._error_count += 1

            if self._is_critical_enabled:
                self.logger.critical('--- CRITICAL ERROR #{} ---'
                                     .format(self._critical_count))
                self._critical_count += 1

    def start(self) -> None:
        if self._is_running:
            return

        self._is_running = True
        self._thread = threading.Thread(target=self.run)
        self._thread.daemon = True
        self._thread.start()
