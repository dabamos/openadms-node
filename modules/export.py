#!/usr/bin/env python3

"""Module for the export of observations."""

__author__ = 'Philipp Engel'
__copyright__ = 'Copyright (c) 2020, Hochschule Neubrandenburg'
__license__ = 'BSD-2-Clause'

# Build-in modules.
import copy
import threading
import time

from enum import Enum
from functools import reduce
from pathlib import Path
from typing import Any, Dict, Union
from urllib.parse import urljoin

# Third-party modules.
import arrow
import requests

from tinydb import TinyDB
from tinydb.storages import MemoryStorage

# OpenADMS Node modules.
from core.manager import Manager
from core.observation import Observation
from core.prototype import Prototype


class CloudExporter(Prototype):
    """
    CloudExporter sends observation data to an OpenADMS Server instance.
    Observations are cached locally in case the service is temporary not
    reachable and then send again. Caching can be done either in-memory or
    file-based. In-memory is faster and requires less I/O operations, but
    cached observations do not persist over restarts (data loss may be occur).

    The JSON-based configuration for this module:

    Parameters:
        server: FQDN of the OpenADMS Server instance.
        user: User name for OpenADMS Server (HTTP Basic Auth).
        password: Password for OpenADMS Server (HTTP Basic Auth).
        db: Path to the cache database file (e.g.: `cache.json`).
        cache: Caching type (either `file` or `memory`).

    Example:
        Example configuration::

            {
                "server": "https://api.examples.com/",
                "user": "test",
                "password": "secret",
                "db": "cache.json",
                "cache": "file"
            }
    """

    def __init__(self, module_name: str, module_type: str, manager: Manager):
        super().__init__(module_name, module_type, manager)
        config = self.get_module_config(self._name)

        self._host = config.get('host')
        self._url = reduce(urljoin, [self._host, 'api/v1/', 'observations/'])

        self._user = config.get('user')
        self._password = config.get('password')
        self._cache = config.get('cache') or 'memory'
        self._db_file = config.get('db')
        self._retry_delay = 10.0
        self._timeout = 10.0
        self._thread = None

        if self._cache not in ['file', 'memory']:
            raise ValueError('Invalid cache type')

        if self._cache == 'memory':
            # Create in-memory cache database.
            self._cache_db = TinyDB(storage=MemoryStorage)
            self.logger.verbose('Created in-memory cache database')

        if self._cache == 'file':
            # Create file-based cache database.
            try:
                self.logger.verbose(f'Opening local cache database '
                                    f'"{self._db_file}" ...')
                self._cache_db = TinyDB(self._db_file)
            except Exception:
                self._cache_db = TinyDB(storage=MemoryStorage)
                raise ValueError(f'Cache database file "{self._db_file}" could not '
                                 f'be opened, using memory storage instead')

    def _cache_observation(self, obs: Observation) -> str:
        """Caches the given observation in the local cache database.

        Args:
            obs: Observation object.
        """
        doc_id = self._cache_db.insert(obs.data)
        self.logger.debug(f'Cached observation "{obs.get("name")}" of target '
                          f'"{obs.get("target")}" (id {doc_id})')
        return doc_id

    def _get_cached_observations(self) -> Union[Dict[str, Any], None]:
        """"Returns a random observation data set from the cache database.

        Returns:
            Observation data or None if cache is empty.
        """
        if len(self._cache_db) > 0:
            return self._cache_db.all()[0]

        return None

    def _remove_observation(self, doc_id: int) -> None:
        """Removes a single observations from the cache database.

        Args:
            doc_id: The document id.
        """
        self._cache_db.remove(doc_ids=[doc_id])
        self.logger.debug('Removed observation from cache '
                          '(id {})'.format(doc_id))

    def _transfer_observation(self, obs_data: Dict[str, Any]) -> bool:
        """Sends an observersation to defined remote OpenADMS Server instance.

        Args:
            obs_data: The observation data dictionary.

        Returns:
            True on successful transmission, False on error.
        """
        try:
            self.logger.info(f'Sending observation "{obs_data.get("name")}" of '
                             f'target "{obs_data.get("target")}" from port '
                             f'"{obs_data.get("portName")}" to API '
                             f'"{self._url}" ...')
            r = requests.post(self._url, auth=(self._user,
                                               self._password),
                                               json=obs_data,
                                               timeout=self._timeout)
        except requests.exceptions.ConnectionError:
            self.logger.warning(f'Connection to API "{self._host}" failed')
            return False
        except requests.exceptions.HTTPError:
            self.logger.warning(f'Invalid response from API "{self._host}"')
            return False
        except requests.exceptions.Timeout:
            self.logger.warning(f'Connection to API "{self._host}" timed out')
            return False
        except requests.exceptions.TooManyRedirects:
            self.logger.warning(f'Too many redirects by API "{self._host}"')
            return False
        except requests.exceptions.RequestException as e:
            self.logger.warning(f'Connection to API "{self._host}" failed: {str(e)}')
            return False

        if (r.status_code == 200 or r.status_code == 201):
            self.logger.info(f'Successfully sent observation "{obs_data.get("name")}" '
                             f'of target "{obs_data.get("target")}" from port '
                             f'"{obs_data.get("portName")}" to API '
                             f'"{self._host}" (server status {r.status_code})')
            return True
        else:
            self.logger.warning(f'Sending observation to API "{self._host}" '
                                f'failed (server error {r.status_code})')

        return False

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
        while self._is_running:
            # Lazy waiting ...
            if not self.has_cached_observation():
                time.sleep(1.0)
                continue

            if len(self._cache_db) > 500:
                self.logger.warning('Cache stores more than 500 observations')

            # Send cached observations to OpenADMS Server.
            obs_data = self._get_cached_observations()

            if self._transfer_observation(obs_data):
                # Remove the transferred observation data from cache.
                self._remove_observation(obs_data.doc_id)
            else:
                # On error, wait before retrying.
                time.sleep(self._retry_delay)

    def start(self) -> None:
        """Starts the module."""
        if self._is_running:
            return

        super().start()

        self._thread = threading.Thread(target=self.run, daemon=True)
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
            'yearly': FileRotation.YEARLY
        }.get(config.get('fileRotation'))
        self._date_time_format = config.get('dateTimeFormat')
        self._separator = config.get('separator')
        self._paths = config.get('paths')
        self._save_observation_id = config.get('saveObservationId')

    def process_observation(self, obs: Observation) -> Observation:
        """Appends data to a flat file in CSV format.

        Args:
            obs: `Observation` object.

        Returns:
            The `Observation` object.
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

        fn = self._file_name
        fn = fn.replace('{{port}}', obs.get("portName"))
        fn = fn.replace('{{date}}', f'{file_date}'
                        if file_date else '')
        fn = fn.replace('{{target}}', f'{obs.get("target")}'
                        if obs.get('target') is not None else '')
        fn = fn.replace('{{name}}', f'{obs.get("name")}'
                        if obs.get('name') is not None else '')
        fn += self._file_extension

        for path in self._paths:
            if not Path(path).exists():
                self.logger.critical(f'Path "{path}" does not exist')
                continue

            file_path = Path(path, fn)

            # Create a header if a new file has to be touched.
            header = None

            if not Path(file_path).is_file():
                header = (f'# Target "{obs.get("target")}" of '
                          f'"{obs.get("sensorName")}" on '
                          f'"{obs.get("portName")}"\n')

            # Open a file for each path.
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

                self.logger.info(f'Saved observation "{obs.get("name")}" of '
                                 f'target "{obs.get("target")}" from port '
                                 f'"{obs.get("portName")}" to file '
                                 f'"{str(file_path)}"')

        return obs


class RealTimePublisher(Prototype):
    """
    RealTimePublisher forwards incoming `Observation` objects by MQTT to a list
    of topics.

    Parameters:
        enabled (bool): Turns processing of observations on or off.
        topics (List): List of topics to send the observations to.

    Example:
        Example configuration::

            {
              "realTimePublisher": {
                "enabled": true,
                "topics": [
                  "onlineViewer"
                ]
              }
            }
    """

    def __init__(self, module_name: str, module_type: str, manager: Manager):
        super().__init__(module_name, module_type, manager)
        config = self.get_module_config(self._name)

        self._topics = config.get('topics')
        self._is_enabled = config.get('enabled')

    def process_observation(self, obs: Observation) -> Observation:
        if not self._is_enabled:
            return obs

        for topic in self._topics:
            obs_copy = copy.deepcopy(obs)

            target = f'{topic}/{obs_copy.get("target")}'

            obs_copy.set('nextReceiver', 0)
            obs_copy.set('receivers', [target])

            self.logger.debug(f'Publishing observation '
                              f'"{obs_copy.get("name")}" of target '
                              f'"{obs_copy.get("target")}" to "{target}"')

            header = Observation.get_header()
            payload = obs_copy.data

            self.publish(target, header, payload)

        return obs
