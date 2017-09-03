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

__author__ = 'Philipp Engel'
__copyright__ = 'Copyright (c) 2017 Hochschule Neubrandenburg'
__license__ = 'EUPL'

from tinydb import TinyDB, Query
from typing import *

from core.manager import Manager
from module.prototype import Prototype


class TinyDBConnectivity(Prototype):

    def __init__(self, name: str, type: str, manager: Manager):
        super().__init__(name, type, manager)
        config = self._config_manager.get(self._name)

        self._path = config.get('path')
        self._db = TinyDB(self._path)

        self.add_handler('tinyQuery', self.process_query)

    def process_query(self, header, payload):
        pass
