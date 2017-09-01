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

"""Main monitoring module."""

__author__ = 'Philipp Engel'
__copyright__ = 'Copyright (c) 2017 Hochschule Neubrandenburg'
__license__ = 'EUPL'

from core.manager import *


class Monitor(object):
    """
    Monitor is used to manage the monitoring process by creating a
    configuration manager, a sensor manager, and a module manager.

    Args:
        config_file_path (str): The path to the configuration file.
    """

    def __init__(self, config_file_path: str):
        manager = Manager()
        manager.schema_manager = SchemaManager()
        manager.config_manager = ConfigManager(config_file_path,
                                               manager.schema_manager)
        manager.sensor_manager = SensorManager(manager.config_manager)
        manager.module_manager = ModuleManager(manager)

