#!/usr/bin/env python3.6

"""Connectivity modules for various NoSQL databases."""

__author__ = 'Philipp Engel'
__copyright__ = 'Copyright (c) 2017 Hochschule Neubrandenburg'
__license__ = 'BSD-2-Clause'

import logging

try:
    import couchdb
except ImportError:
    logging.getLogger().critical('Importing Python module "couchdb" failed')

from tinydb import TinyDB
from tinydb.storages import MemoryStorage

from core.manager import Manager
from core.observation import Observation
from modules.prototype import Prototype


class CouchDriver(Prototype):
    """
    CouchDriver provides connectivity for Apache CouchDB. Observations send to
    a CouchDriver instance will be saved in the database set in the
    configuration. This module is for dumping observations only.

    The JSON-based configuration for this module:

    Parameters:
        server (str): FQDN or IP address of CouchDB server.
        port (int): Port number of CouchDB server.
        db (str): Database name.
        tls (bool): Use TLS encryption (default: False).
    """

    def __init__(self, module_name: str, module_type: str, manager: Manager):
        super().__init__(module_name, module_type, manager)
        config = self.get_module_config(self._name)

        # HTTPS or HTTP.
        tls = config.get('tls', False)
        self._scheme = 'https' if tls else 'http'

        # CouchDB server.
        self._server = config.get('server')
        self._port = config.get('port')

        # CouchDB user and password.
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

            self.logger.info('Opening CouchDB database "{}"'
                             .format(self._db_name))
            self._db = self._couch[self._db_name]

    def process_observation(self, obs: Observation) -> Observation:
        self._connect()

        # Save document in CouchDB database.
        try:
            self._db[obs.get('id')] = obs.data
            self.logger.info('Saved observation "{}" of target "{}" from '
                             'port "{}" to CouchDB database "{}"'
                             .format(obs.get('name'),
                                     obs.get('target'),
                                     obs.get('portName'),
                                     self._db_name))
        except Exception:
            self.logger.error('Observation "{}" of target "{}" from port "{}" '
                              'could not be saved in CouchDB database "{}"'
                              .format(obs.get('name'),
                                      obs.get('target'),
                                      obs.get('portName'),
                                      self._db_name))

        return obs
