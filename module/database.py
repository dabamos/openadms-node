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

import logging

try:
    import couchdb
except ImportError:
    logging.getLogger().error('Importing Python module "couchdb" failed')

from core.manager import Manager
from core.observation import Observation
from module.prototype import Prototype


class CouchDriver(Prototype):

    def __init__(self, module_name: str, module_type: str, manager: Manager):
        super().__init__(module_name, module_type, manager)
        config = self.get_config(self._name)

        # HTTPS or HTTP.
        tls = config.get('tls')
        self._scheme = 'https' if tls else 'http'

        # CouchDB server.
        self._server = config.get('server')
        self._port = config.get('port')

        # CouchDB user.
        user = config.get('user')
        password = config.get('password')

        # URL to CouchDB server.
        self._server_url = '{}://{}:{}@{}:{}/'.format(self._scheme,
                                                      user,
                                                      password,
                                                      self._server,
                                                      self._port)
        self._db_name = config.get('db')

        self._couch = None
        self._db = None

    def _connect(self) -> None:
        """Connects to CouchDB database server."""
        if not self._couch:
            self.logger.info('Connecting to CouchDB server "{}://{}:{}/"'
                             .format(self._scheme, self._server, self._port))
            self._couch = couchdb.Server(self._server_url)

        if not self._db:
            self.logger.info('Opening CouchDB database "{}"'
                             .format(self._db_name))
            self._db = self._couch[self._db_name]

    def process_observation(self, obs: Observation) -> Observation:
        self._connect()

        # Save document to CouchDB database.
        self._db[obs.get('id')] = obs.data

        self.logger.info('Saved observation "{}" of target "{}" from port "{}" '
                         'to CouchDB database "{}"'
                         .format(obs.get('name'),
                                 obs.get('target'),
                                 obs.get('portName'),
                                 self._db_name))

        return obs
