#!/usr/bin/env python3

"""Main monitoring module. Everything starts here."""

__author__ = 'Philipp Engel'
__copyright__ = 'Copyright (c) 2019, Hochschule Neubrandenburg'
__license__ = 'BSD-2-Clause'

import logging
import time

from core.manager import (ConfigManager, Manager, ModuleManager, NodeManager,
                          ProjectManager, SchemaManager, SensorManager)


class Monitor:
    """
    Monitor is used to manage the monitoring process by creating a schema
    manager, configuration manager, a sensor manager, and a module manager.
    """

    def __init__(self, config_file_path: str):
        """
        Args:
            config_file_path: The path to the OpenADMS Node configuration file.
        """
        self.logger = logging.getLogger('monitor')
        self._config_file_path = config_file_path
        manager = Manager()

        try:
            manager.schema = SchemaManager()
            manager.config = ConfigManager(self._config_file_path,
                                           manager.schema)
            manager.project = ProjectManager(manager)
            manager.node = NodeManager(manager)
            manager.sensor = SensorManager(manager.config)
            manager.module = ModuleManager(manager)
        except ValueError as e:
            self.logger.error(f'Fatal error: {e}')

        self._manager = manager

    def kill_all(self) -> None:
        """Kills all modules"""
        self._manager.module.kill_all()

    def load_all(self) -> None:
        """Calls managers to load and initialise everything."""
        self._manager.schema.load_all()
        self._manager.config.load_all()
        self._manager.project.load_all()
        self._manager.node.load_all()
        self._manager.sensor.load_all()
        self._manager.module.load_all()

    def start(self) -> None:
        """Starts all modules."""
        if self._manager.module:
            self._manager.module.start_all()

    def stop(self) -> None:
        """Stops all modules."""
        self._manager.module.stop_all()

    def remove_all(self) -> None:
        """Clears all managers."""
        self._manager.sensor.remove_all()
        self._manager.node.remove_all()
        self._manager.project.remove_all()
        self._manager.config.remove_all()
        self._manager.schema.remove_all()

    def restart(self) -> None:
        """Clears and restarts everything."""
        self.logger.notice('Restarting everything ...')

        self.kill_all()
        time.sleep(3.0)

        self.remove_all()
        self.load_all()
        self.start()
