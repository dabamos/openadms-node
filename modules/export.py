#!/usr/bin/env python3.6

"""Module for the export of observations."""

__author__ = 'Philipp Engel'
__copyright__ = 'Copyright (c) 2017 Hochschule Neubrandenburg'
__license__ = 'BSD-2-Clause'

import copy
import threading
import time

from enum import Enum
from pathlib import Path
from typing import *

import arrow
import requests

from tinydb import TinyDB
from tinydb.storages import MemoryStorage

from core.manager import Manager
from core.observation import Observation
from modules.prototype import Prototype


class CloudExporter(Prototype):
    """
    CloudExporter sends observation data to an OpenADMS Server instance.
    Observations are cached locally in case the service is temporary not
    reachable and then send again. Caching can be done either in-memory or
    file-based. In-memory is faster and requires less I/O operations, but
    cached observations do not persist over restarts (data loss may be occur).

    The JSON-based configuration for this module:

    Parameters:
        url: URL of the OpenADMS Server instance.
        user: User name for OpenADMS Server.
        password: Password for OpenADMS Server.
        authMethod: Authentication method (`basic` or `jwt`).
        db: File name of the cache database (e.g.: ``cache.json``).
        storage: Storage type (`file` or `memory`).

    Example:
        The configuration may be::

            {
                "url": "https://api.examples.com/",
                "user": "test",
                "password": "secret",
                "authMethod": "basic",
                "db": "cache.json",
                "storage": "file"
            }
    """

    def __init__(self, module_name: str, module_type: str, manager: Manager):
        super().__init__(module_name, module_type, manager)
        config = self.get_module_config(self._name)

        self._url = config.get('url')
        self._user = config.get('user')
        self._password = config.get('password')
        self._auth_method = config.get('authMethod')
        self._storage = config.get('storage')
        self._db_file = config.get('db')

        self._jwt_token = None
        self._thread = None

        if self._storage not in ['file', 'memory']:
            raise ValueError('Invalid storage method')

        if self._storage == 'memory':
            self._cache_db = TinyDB(storage=MemoryStorage)
            self.logger.info('Created in-memory cache database')

        if self._storage == 'file':
            try:
                self._cache_db = TinyDB(self._db_file)
                self.logger.info('Opened cache database "{}"'
                                 .format(self._db_file))
            except Exception:
                raise ValueError('Cache database "{}" could not be opened'
                                 .format(self._db_file))

    def _cache_observation(self, obs: Observation) -> str:
        """Caches the given observation in the local cache database.

        Args:
            obs: Observation object.
        """
        doc_id = self._cache_db.insert(obs.data)
        self.logger.debug('Cached observation "{}" with target "{}" '
                          '(document id = {})'.format(obs.get('name'),
                                                      obs.get('target'),
                                                      doc_id))
        return doc_id

    def _get_cached_observation_data(self) -> Union[Dict[str, Any], None]:
        """"Returns a random observation data set from the cache database.

        Returns:
            Observation data or None if cache is empty.
        """
        if len(self._cache_db) > 0:
            return self._cache_db.all()[0]

        return None

    def _remove_observation_data(self, doc_id: int) -> None:
        """Removes a single observations from the cache database.

        Args:
            doc_id: Document id.
        """
        self._cache_db.remove(doc_ids=[doc_id])
        self.logger.debug('Removed observation from cache database '
                          '(document id = {})'.format(doc_id))

    def _transfer_observation_data(self, obs_data: Dict[str, Any]) -> bool:
        # TODO this method is a mock
        self.logger.info('Transferred observation "{}" with target "{}"'
                         .format(obs_data.get('name'),
                                 obs_data.get('target')))
        return True

    def has_cached_observation(self) -> bool:
        """Returns whether or not a cached observation exists in the database.

        Returns:
            True if cached observation exists, False if not.
        """
        return True if len(self._cache_db) > 0 else False

    def process_observation(self, obs: Observation) -> Observation:
        """Caches observation object locally.

        Args:
            obs: Observation object.

        Returns:
            The observation object.
        """
        self._cache_observation(copy.deepcopy(obs))
        return obs

    def run(self) -> None:
        """Sends cached observation to RESTful service."""
        while self.is_running:
            if not self.has_cached_observation_data():
                time.sleep(1.0)
                continue

            if len(self._cache_db) > 500:
                self.logger.warning('Cache is running full '
                                    '(> 500 observations)')

            # Send cached observation data to OpenADMS Server.
            obs_data = self._get_cached_observation_data()
            is_transferred = self._transfer_observation_data(obs_data)

            if is_transferred:
                # Remove the transferred observation data from cache.
                self._remove_observation_data(obs_data.doc_id)

    def start(self) -> None:
        """Starts the module."""
        if self._is_running:
            return

        super().start()

        self._thread = threading.Thread(target=self.run)
        self._thread.daemon = True
        self._thread.start()


class FileRotation(Enum):
    """
    Enumeration of file rotation times of flat files.
    """

    NONE = 0
    DAILY = 1
    MONTHLY = 2
    YEARLY = 3


class FileExporter(Prototype):
    """
    FileExporter writes sensor data to a flat file in CSV format.

    The JSON-based configuration for this module:

    Parameters:
        dateTimeFormat (str): Format of date and time (see `arrow` library).
        fileExtension (str): Extension of the file (``.txt`` or ``.csv``).
        fileName (str): File name with optional placeholders ``{{date}}``,
            ``{{target}}``, ``{{name}}``, ``{{port}}``.
        fileRotation (str): Either ``none``, ``daily``, ``monthly``, or
            ``yearly``.
        paths (List[str]): Paths to save files to (multiple paths possible).
        separator (str): Separator between values within the CSV file.

    """

    def __init__(self, module_name: str, module_type: str, manager: Manager):
        super().__init__(module_name, module_type, manager)
        config = self.get_module_config(self._name)

        self._file_extension = config.get('fileExtension')
        self._file_name = config.get('fileName')
        self._file_rotation = {
            'none': FileRotation.NONE,
            'daily': FileRotation.DAILY,
            'monthly': FileRotation.MONTHLY,
            'yearly': FileRotation.YEARLY}.get(config.get('fileRotation'))
        self._date_time_format = config.get('dateTimeFormat')
        self._separator = config.get('separator')
        self._paths = config.get('paths')
        self._save_observation_id = config.get('saveObservationId')

    def process_observation(self, obs: Observation) -> Observation:
        """Appends data to a flat file in CSV format.

        Args:
            obs: Observation object.

        Returns:
            The observation object.
        """
        ts = arrow.get(obs.get('timestamp', 0))

        file_date = {
            # No file rotation, i.e., all data is stored in a single file.
            FileRotation.NONE: None,
            # Every day a new file is created.
            FileRotation.DAILY: ts.format('YYYY-MM-DD'),
            # Every month a new file is created.
            FileRotation.MONTHLY: ts.format('YYYY-MM'),
            # Every year a new file is created.
            FileRotation.YEARLY: ts.format('YYYY')
        }[self._file_rotation]

        file_name = self._file_name
        file_name = file_name.replace('{{port}}', obs.get('portName'))
        file_name = file_name.replace('{{date}}', '{}'.format(file_date)
                                      if file_date else '')
        file_name = file_name.replace('{{target}}', '{}'
                                      .format(obs.get('target'))
                                      if obs.get('target') is not None else '')
        file_name = file_name.replace('{{name}}', '{}'.format(obs.get('name'))
                                      if obs.get('name') is not None else '')
        file_name += self._file_extension

        for path in self._paths:
            if not Path(path).exists():
                self.logger.error('Path "{}" does not exist'.format(path))
                continue

            file_path = Path(path, file_name)

            # Create a header if a new file has to be touched.
            header = None

            if not Path(file_path).is_file():
                header = '# Target "{}" of "{}" on "{}"\n' \
                         .format(obs.get('target'),
                                 obs.get('sensorName'),
                                 obs.get('portName'))

            # Open a file for every path.
            with open(str(file_path), 'a') as fh:
                # Add the header if necessary.
                if header:
                    fh.write(header)

                # Format the time stamp. For more information, see:
                # http://arrow.readthedocs.io/en/latest/#tokens
                date_time = ts.format(self._date_time_format)

                # Create the CSV line starting with date and time.
                line = date_time

                if self._save_observation_id:
                    line += self._separator + obs.get('id')

                if obs.get('target') is not None:
                    line += self._separator + obs.get('target')

                response_sets = obs.get('responseSets')

                for response_set_id in sorted(response_sets.keys()):
                    response_set = response_sets.get(response_set_id)

                    v = response_set.get('value')
                    u = response_set.get('unit')

                    line += self._separator + format(response_set_id)
                    line += self._separator + format(v)
                    line += self._separator + format(u)

                # Write line to file.
                fh.write(line + '\n')

                self.logger.verbose('Saved observation "{}" of target "{}" '
                                    'from port "{}" to file "{}"'
                                    .format(obs.get('name'),
                                            obs.get('target'),
                                            obs.get('portName'),
                                            str(file_path)))

        return obs


class RealTimePublisher(Prototype):
    """
    RealTimePublisher sends copies of `Observation` objects to a list of
    receivers.

    The JSON-based configuration for this module:

    Parameters:
        receivers (List): List of modules to send the observation to.
        enabled (bool): Turns processing of observations on or off.
    """

    def __init__(self, module_name: str, module_type: str, manager: Manager):
        super().__init__(module_name, module_type, manager)
        config = self.get_module_config(self._name)

        self._receivers = config.get('receivers')
        self._is_enabled = config.get('enabled')

    def process_observation(self, obs: Observation) -> Observation:
        if not self._is_enabled:
            return obs

        for receiver in self._receivers:
            obs_copy = copy.deepcopy(obs)

            target = receiver + '/' + obs_copy.get('target')

            obs_copy.set('nextReceiver', 0)
            obs_copy.set('receivers', [target])

            self.logger.debug('Publishing observation "{}" of target "{}" '
                              'to "{}"'.format(obs_copy.get('name'),
                                               obs_copy.get('target'),
                                               target))

            header = Observation.get_header()
            payload = obs_copy.data

            self.publish(target, header, payload)

        return obs
