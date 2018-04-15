#!/usr/bin/env python3.6

"""Connectivity modules for various NoSQL databases."""

__author__ = 'Philipp Engel'
__copyright__ = 'Copyright (c) 2018 Hochschule Neubrandenburg'
__license__ = 'BSD-2-Clause'

import logging
import threading
import time

from typing import *

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
        path (str): Additional URI path or blank.
        port (int): Port number of CouchDB server.
        user (str): User name.
        password (str): Password.
        db (str): Database name.
        tls (bool): Use TLS encryption (default: False).
        cacheFile (str): Optional file name of local cache database
            (e.g., `cache.json`). If not set, an in-memory database will be
            used instead.
    """

    def __init__(self, module_name: str, module_type: str, manager: Manager):
        super().__init__(module_name, module_type, manager)
        config = self.get_module_config(self._name)

        self._couch = None      # CouchDB driver.
        self._db = None         # CouchDB database.
        self._thread = None     # Thread doing the caching.

        # Initialise local cache database.
        cache_file = config.get('cacheFile')

        if not cache_file or cache_file.strip() == "":
            # Create in-memory cache database.
            self.logger.info('Creating in-memory cache database ...')
            self._cache_db = TinyDB(storage=MemoryStorage)
        else:
            # Create file-based cache database.
            self.logger.info('Opening local cache database "{}" ...'
                             .format(cache_file))
            self._cache_db = TinyDB(cache_file)

        # HTTPS or HTTP.
        is_tls = config.get('tls', False)
        self._scheme = 'https' if is_tls else 'http'

        # CouchDB server.
        self._server = config.get('server')
        self._path = config.get('path', '')
        self._port = config.get('port', 5984)
        user = config.get('user')
        password = config.get('password')

        # URI to CouchDB server, for example:
        # https://<user>:<password>@iot.example.com:443/couchdb/
        self._server_uri = '{}://{}:{}@{}:{}/{}'.format(self._scheme,
                                                        user,
                                                        password,
                                                        self._server,
                                                        self._port,
                                                        self._path)
        # Database to open.
        self._db_name = config.get('db')

    def _cache_observation_data(self, obs: Observation) -> str:
        """Caches the given observation in local cache database.

        Args:
            obs: Observation object.
        """
        doc_id = self._cache_db.insert(obs.data)

        return doc_id

    def _connect(self) -> None:
        """Connects to CouchDB database server."""
        try:
            self.logger.info('Connecting to CouchDB server "{}://{}:{}/{}" ...'
                             .format(self._scheme,
                                     self._server,
                                     self._port,
                                     self._path))
            self._couch = couchdb.Server(self._server_uri)

            if self._db_name not in self._couch:
                self.logger.error('Database "{}" not found on server "{}"'
                                  .format(self._db_name, self._server_uri))
                return

            self.logger.info('Opening CouchDB database "{}" ...'
                             .format(self._db_name))
            self._db = self._couch[self._db_name]
        except Exception as e:
            self.logger.error('Failed to connect to CouchDB database: {}'
                              .format(e))

    def _get_cached_observation_data(self) -> Union[Dict[str, Any], None]:
        """"Returns a random observation data set from the local cache database.

        Returns:
            Observation data or None if cache is empty.
        """
        if len(self._cache_db) > 0:
            return self._cache_db.all()[0]

        return None

    def _insert_observation_data(self, obs_data: Dict[str, Any]) -> bool:
        """Inserts observation data into CouchDB database.

        Args:
            obs_data: The observation data.

        Returns:
            True on success, False on failure.
        """
        try:
            if self._couch is None:
                self._connect()

            self._db[obs_data.get('id')] = obs_data
            self.logger.info('Saved observation "{}" of target "{}" from '
                             'port "{}" to CouchDB database "{}"'
                             .format(obs_data.get('name'),
                                     obs_data.get('target'),
                                     obs_data.get('portName'),
                                     self._db_name))
        except Exception as e:
            self.logger.error('Observation "{}" of target "{}" from port "{}" '
                              'could not be saved in CouchDB database "{}": {}'
                              .format(obs_data.get('name'),
                                      obs_data.get('target'),
                                      obs_data.get('portName'),
                                      self._db_name),
                                      e)
            return False

        return True

    def _remove_observation_data(self, doc_id: int) -> None:
        """Removes a single observations from the local cache database.

        Args:
            doc_id: The document id.
        """
        self._cache_db.remove(doc_ids=[doc_id])
        self.logger.debug('Removed observation from cache database '
                          '(doc id = {})'.format(doc_id))

    def has_cached_observation_data(self) -> bool:
        """Returns whether or not a cached observation exists in the local
        cache database.

        Returns:
            True if cached observation exists, False if not.
        """
        return True if len(self._cache_db) > 0 else False

    def process_observation(self, obs: Observation) -> Observation:
        doc_id = self._cache_observation_data(obs)

        if doc_id:
            self.logger.debug('Cached observation "{}" with target "{}" '
                              '(doc id = {})'.format(obs.get('name'),
                                                     obs.get('target'),
                                                     doc_id))
        else:
            self.logger.error('Caching of observation "{}" with target "{}" '
                              'failed'.format(obs.get('name'),
                                              obs.get('target')))

        return obs

    def run(self) -> None:
        """Inserts cached observations into CouchDB database."""
        while self.is_running:
            if not self.has_cached_observation_data():
                time.sleep(1.0)
                continue

            if len(self._cache_db) > 500:
                self.logger.warning('Cache database is running full '
                                    '({} cached observations)'
                                    .format(len(self._cache_db)))

            # Insert cached observation data into CouchDB database.
            obs_data = self._get_cached_observation_data()

            if obs_data:
                self.logger.debug('Trying to insert observation "{}" with '
                                  'target "{}" (doc id = {}) into CouchDB '
                                  'database "{}" ...'
                                  .format(obs_data.get('name'),
                                          obs_data.get('target'),
                                          obs_data.doc_id,
                                          self._db_name))

                # Remove the inserted observation data from local cache.
                if self._insert_observation_data(obs_data):
                    self._remove_observation_data(obs_data.doc_id)

    def start(self) -> None:
        """Starts the module."""
        if self._is_running:
            return

        super().start()

        self._thread = threading.Thread(target=self.run)
        self._thread.daemon = True
        self._thread.start()
