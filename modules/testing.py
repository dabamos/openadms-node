#!/usr/bin/env python3.6

"""Module for testing the monitoring system."""

__author__ = 'Philipp Engel'
__copyright__ = 'Copyright (c) 2017 Hochschule Neubrandenburg'
__license__ = 'BSD (2-Clause)'

import threading
import time

from core.manager import Manager
from modules.prototype import Prototype


class ErrorGenerator(Prototype):
    """
    ErrorGenerates creates `warning`, `error`, or `critical` log messages in a
    given interval for testing purposes.

    The JSON-based configuration for this modules:

    Parameters:
        warning (bool): Enable warning messages.
        error (bool): Enable error messages.
        critical (bool): Enable critical messages.
        interval (float): Interval to create log messages (in seconds).
    """

    def __init__(self, module_name: str, module_type: str, manager: Manager):
        super().__init__(module_name, module_type, manager)
        config = self.get_module_config(self._name)

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
                self.logger.warning('WARNING #{}'
                                    .format(self._warning_count))
                self._warning_count += 1

            if self._is_error_enabled:
                self.logger.error('ERROR #{}'
                                  .format(self._error_count))
                self._error_count += 1

            if self._is_critical_enabled:
                self.logger.critical('CRITICAL ERROR #{}'
                                     .format(self._critical_count))
                self._critical_count += 1

    def start(self) -> None:
        """Starts the modules."""
        if self._is_running:
            return

        super().start()

        self._thread = threading.Thread(target=self.run)
        self._thread.daemon = True
        self._thread.start()
