#!/usr/bin/env python3.6

"""Main monitoring module. Everything starts here."""

__author__ = 'Philipp Engel'
__copyright__ = 'Copyright (c) 2017 Hochschule Neubrandenburg'
__license__ = 'EUPL'

from core.manager import *


class Monitor(object):
    """
    Monitor is used to manage the monitoring process by creating a
    configuration manager, a sensor manager, and a module manager.
    """

    def __init__(self, config_file_path: str):
        """
        Args:
            config_file_path: The path to the configuration file.
        """
        self.logger = logging.getLogger('monitor')
        manager = Manager()

        try:
            manager.schema_manager = SchemaManager()
            manager.config_manager = ConfigManager(config_file_path,
                                                   manager.schema_manager)
            manager.project_manager = ProjectManager(manager)
            manager.node_manager = NodeManager(manager)
            manager.sensor_manager = SensorManager(manager.config_manager)
            manager.module_manager = ModuleManager(manager)
        except ValueError as e:
            self.logger.error(e)

        self._manager = manager

    def start(self) -> None:
        """Starts all modules."""
        if self._manager.module_manager:
            self._manager.module_manager.start_all()
