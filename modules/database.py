#!/usr/bin/env python3

"""Connectivity modules for various NoSQL databases."""

__author__ = 'Philipp Engel'
__copyright__ = 'Copyright (c) 2019, Hochschule Neubrandenburg'
__license__ = 'BSD-2-Clause'

import logging
import threading
import time

from typing import Any, Dict, Union

try:
    import couchdb
except ImportError:
    logging.getLogger().warning('Importing Python module "couchdb" failed')

try:
    from tinydb import TinyDB
    from tinydb.storages import MemoryStorage
except ImportError:
    logging.getLogger().warning('Importing Python module "tinydb" failed')

from core.manager import Manager
from core.observation import Observation
from core.prototype import Prototype


class CouchDriver(Prototype):
    """
    CouchDriver provides connectivity for Apache CouchDB. Observations send to
    a CouchDriver instance will be cached and then stored in the database
    defined the configuration. TinyDB is used for caching (either file-based
    or in-memory).

    The JSON-based configuration for this module:

    Parameters:
        server (str): FQDN or IP address of CouchDB server.
        path (str): Additional CouchDB instance path or blank.
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
        self._timeout = 30.0    # Time to wait on connection error.

        cache_file = config.get('cacheFile')

        # Initialise local cache database.
        if not cache_file or cache_file.strip() == "":
            # Create in-memory cache database.
            self.logger.verbose('Creating in-memory cache database ...')
            self._cache_db = TinyDB(storage=MemoryStorage)
        else:
            # Create file-based cache database.
            try:
                self.logger.verbose(f'Opening local cache database '
                                    f'"{cache_file}" ...')
                self._cache_db = TinyDB(cache_file)
            except Exception:
                raise ValueError(f'Cache database "{self._db_file}" could '
                                 f'not be opened')

        # Use either HTTPS or HTTP.
        is_tls = config.get('tls', False)
        self._scheme = 'https' if is_tls else 'http'

        # Configuration of the CouchDB server.
        self._server = config.get('server')
        self._path = config.get('path', '')
        self._port = config.get('port', 5984)
        user = config.get('user')
        password = config.get('password')

        # Generate URI to CouchDB server, for example:
        # https://<user>:<password>@iot.example.com:443/couchdb/
        self._server_uri = (f'{self._scheme}://{user}:{password}@{self._server}'
                            f':{self._port}/{self._path}')
        # Set name of database to open.
        self._db_name = config.get('db')

    def _cache_observation_data(self, obs: Observation) -> str:
        """Caches the given observation in local cache database.

        Args:
            obs: The observation object.

        Returns:
            Document id of cached data set.
        """
        doc_id = self._cache_db.insert(obs.data)
        return doc_id

    def _connect(self) -> None:
        """Connects to CouchDB database server.

        Raises:
            Exception: On connection error.
        """
        # Connect to CouchDB server.
        self.logger.info(f'Connecting to CouchDB server "{self._scheme}://'
                         f'{self._server}:{self._port}/{self._path}" ...')
        self._couch = couchdb.Server(self._server_uri)

        # Open database.
        if self._db_name not in self._couch:
            self.logger.error(f'Database "{self._db_name}" not found on server '
                              f'"{self._server_uri}"')

        self.logger.info(f'Opening CouchDB database "{self._db_name}" ...')
        self._db = self._couch[self._db_name]

    def _get_cached_observation_data(self) -> Union[Dict[str, Any], None]:
        """"Returns a random JSON-serialised observation data set from the
        local cache database.

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
            self.logger.info(f'Saved observation "{obs_data.get("name")}" of '
                             f'target "{obs_data.get("target")}" from '
                             f'port "{obs_data.get("portName")}" to CouchDB '
                             f'database "{self._db_name}"')
        except Exception as e:
            self.logger.error(f'Observation "{obs_data.get("name")}" with '
                              f'target "{obs_data.get("target")}" from port '
                              f'"{obs_data.get("portName")}" could not be '
                              f'saved in CouchDB database "{self._db_name}": '
                              f'{e}')
            return False

        return True

    def _remove_observation_data(self, doc_id: int) -> None:
        """Removes a single observations from the local cache database.

        Args:
            doc_id: The document id.
        """
        self._cache_db.remove(doc_ids=[doc_id])
        self.logger.debug(f'Removed observation from cache (doc id = {doc_id})')

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
            self.logger.debug(f'Cached observation "{obs.get("name")}" of '
                              f'target "{obs.get("target")}" (doc id = '
                              f'{doc_id})')
        else:
            self.logger.error(f'Caching of observation "{obs.get("name")}" of '
                              f'target "{obs.get("target")}" failed')

        return obs

    def run(self) -> None:
        """Inserts cached observation data into CouchDB database."""
        while self.is_running:
            # Poor men's event handling ...
            if not self.has_cached_observation_data():
                time.sleep(1.0)
                continue

            if len(self._cache_db) > 500:
                self.logger.warning('Cache database is running full '
                                    '({} cached observations)'
                                    .format(len(self._cache_db)))

            # Insert cached observation data into CouchDB database.
            obs_data = self._get_cached_observation_data()

            if not obs_data:
                continue

            self.logger.debug(f'Trying to insert observation '
                              f'"{obs_data.get("name")}" of target '
                              f'"{obs_data.get("target")}" '
                              f'(doc id = {obs_data.doc_id}) into CouchDB '
                              f'database "{self._db_name}" ...')

            # Remove the inserted observation data from local cache.
            if self._insert_observation_data(obs_data):
                self._remove_observation_data(obs_data.doc_id)
            else:
                time.sleep(self._timeout)

    def start(self) -> None:
        """Starts the module."""
        if self._is_running:
            return

        super().start()

        self._thread = threading.Thread(target=self.run)
        self._thread.daemon = True
        self._thread.start()


class TinyDriver(Prototype):
    """
    TinyDriver stores observations in a TinyDB document store.

    The JSON-based configuration for this module:

    Parameters:
        path (str): Path to the database file.
    """

    def __init__(self, module_name: str, module_type: str, manager: Manager):
        super().__init__(module_name, module_type, manager)
        config = self.get_module_config(self._name)

        self._path = config.get('path')

    def process_observation(self, obs: Observation) -> Observation:
        try:
            self.logger.debug(f'Opening TinyDB document store '
                              f'"{self._path}" ...')
            db = TinyDB(self._path)

            doc_id = db.insert(obs.data)
            self.logger.verbose(f'Saved observation "{obs.get("name")}" of '
                                f'target "{obs.get("target")}" in document '
                                f'store "{self._path}" (doc id = {doc_id})')

            db.close()
            self.logger.debug(f'Closed TinyDB document store'
                              f'"{self._path}" ...')
        except Exception as e:
            self.logger.critical(f'Could not access document store '
                                 f'"{self._path}": {str(e)}')

        return obs
