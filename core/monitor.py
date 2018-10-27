#!/usr/bin/env python3.6

"""Main monitoring module. Everything starts here."""

__author__ = 'Philipp Engel'
__copyright__ = 'Copyright (c) 2018 Hochschule Neubrandenburg'
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
            manager.schema_manager = SchemaManager()
            manager.config_manager = ConfigManager(self._config_file_path,
                                                   manager.schema_manager)
            manager.project_manager = ProjectManager(manager)
            manager.node_manager = NodeManager(manager)
            manager.sensor_manager = SensorManager(manager.config_manager)
            manager.module_manager = ModuleManager(manager)
        except ValueError as e:
            self.logger.error(f'Fatal error: {e}')

        self._manager = manager

    def load_all(self) -> None:
        """Calls managers to load and initialise everything."""
        self._manager.schema_manager.load_all()
        self._manager.config_manager.load_all()
        self._manager.project_manager.load_all()
        self._manager.node_manager.load_all()
        self._manager.sensor_manager.load_all()
        self._manager.module_manager.load_all()

    def start(self) -> None:
        """Starts all modules."""
        if self._manager.module_manager:
            self._manager.module_manager.start_all()

    def stop(self) -> None:
        """Stops all modules."""
        self._manager.module_manager.stop_all()

    def kill(self) -> None:
        """Kills all modules"""
        self._manager.module_manager.kill_all()

    def remove_all(self) -> None:
        """Clears all managers."""
        self._manager.sensor_manager.remove_all()
        self._manager.node_manager.remove_all()
        self._manager.project_manager.remove_all()
        self._manager.config_manager.remove_all()
        self._manager.schema_manager.remove_all()

    def restart(self) -> None:
        """Clears and restarts everything."""
        self.logger.notice('Restarting everything ...')

        self.kill()
        time.sleep(3.0)

        self.remove_all()
        self.load_all()
        self.start()
