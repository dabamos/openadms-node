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
__copyright__ = 'Copyright (C) 2017 Hochschule Neubrandenburg'
__license__ = 'EUPL'

import json
import logging
import uuid

from typing import *

# Type definition for the value inside a response set of an observation.
# `ResponseType` can either be of type float, int, or str.
ResponseType = TypeVar('ResponseType', float, int, str)
ValueType = TypeVar('ValueType', float, int, str, List, Dict)

logger = logging.getLogger('observation')


class Observation(object):
    """
    Stores all information regarding a request to and a response by a sensor in
    a dictionary. Filled with initial information from the configuration file
    and later supplemented by data of the processing modules. Can easily be
    transformed to JSON format.
    """

    def __init__(self, data=None):
        if not data:
            self._data = {
                'enabled': True,
                'id': str(uuid.uuid4()),
                'name': 'default',
                'nextReceiver': 0,
                'onetime': False,
                'portName': None,
                'receivers': [],
                'response': None,
                'responseSets': {},
                'sleepTime': 0,
                'target': 'default',
                'timeStamp': None
            }
        else:
            self._data = data

    @staticmethod
    def create_response_set(type: str,
                            unit: str,
                            value: ResponseType) -> Dict[str, ResponseType]:
        """Creates a response set containing type, unit, and value.

        Args:
            type: Type of the response (e.g., 'float').
            unit: Unit of the response (e.g., 'm').
            value: The value of the response (e.g., '17.53').

        Returns:
            Dictionary with type, unit, and value.
        """
        return {
            'type': type,
            'unit': unit,
            'value': value
        }

    def get(self, key: str, default: Any = None) -> ValueType:
        """Returns the value to a given key.

        Args:
            key: The key of the value.
            default: Default return value.

        Returns:
            Single value from the observation data.
        """
        return self._data.get(key, default)

    @staticmethod
    def get_header() -> Dict[str, str]:
        """Returns the header of an observation message.

        Returns:
            Dictionary with header information.
        """
        return {
            'type': 'observation'
        }

    def get_response_type(self, name: str) -> str:
        """Returns the type of a given response set.

        Args:
            name: Name of the response set.

        Returns:
            Type of the response set.
        """
        try:
            t = self._data.get('responseSets').get(name).get('type')
        except AttributeError:
            logger.warning('Type of response set "{}" is missing in '
                           'observation "{}" of target "{}"'
                           .format(name,
                                   self.get('name'),
                                   self.get('target')))

        return t

    def get_response_unit(self, name: str) -> str:
        """Returns the unit of a given response set.

        Args:
            name: Name of the response set.

        Returns:
            Unit of the response set.
        """
        u = ''

        try:
            u = self._data.get('responseSets').get(name).get('value')
        except AttributeError:
            logger.warning('Unit of response set "{}" is missing in '
                           'observation "{}" of target "{}"'
                           .format(name,
                                   self.get('name'),
                                   self.get('target')))

        return u

    def get_response_value(self, name: str) -> ResponseType:
        """Returns the value of a given response set.

        Args:
            name: Name of the response set.

        Returns:
            Value of the response set.
        """
        v = None

        try:
            v = self._data.get('responseSets').get(name).get('value')
        except AttributeError:
            logger.warning('Value of response set "{}" is missing in '
                           'observation "{}" of target "{}"'
                           .format(name,
                                   self.get('name'),
                                   self.get('target')))

        return v

    def get_value(self, *args: str) -> ResponseType:
        """Returns the value of a set of keys.

        Args:
            *args: The keys.

        Returns:
            Single value from the observation data.
        """
        ref = self._data

        for x in args:
            try:
                ref = ref.get(x)
            except AttributeError:
                return

        return ref

    def has_response_type(self, name: str) -> bool:
        """Returns whether the type of a given response set exists or not.

        Args:
            name: Name of the response set.

        Returns:
            True if type exists, else if not.
        """
        try:
            if self._data.get('responseSets')\
                         .get(name)\
                         .get('type') is not None:
                return True
        except AttributeError:
            return False

        return False

    def has_response_unit(self, name: str) -> bool:
        """Returns whether the unit of a given response set exists or not.

        Args:
            name: Name of the response set.

        Returns:
            True if unit exists, else if not.
        """
        try:
            if self._data.get('responseSets')\
                         .get(name)\
                         .get('unit') is not None:
                return True
        except AttributeError:
            return False

        return False

    def has_response_value(self, name: str) -> bool:
        """Returns whether the value of a given response set exists or not.

        Args:
            name: Name of the response set.

        Returns:
            True if value exists, else if not.
        """
        try:
            if self._data.get('responseSets')\
                         .get(name)\
                         .get('value') is not None:
                return True
        except AttributeError:
            return False

        return False

    def set(self, key: str, value: Any) -> None:
        """Sets key and value in the data set.

        Args:
            key: The key of the data set value.
            value: The data set value.
        """
        self._data[key] = value

    def to_json(self) -> str:
        """Returns a dump of the data set in JSON format.

        Returns:
            str: Data in JSON format.
        """
        return json.dumps(self._data)

    @property
    def data(self) -> Dict[str, Any]:
        return self._data

    @data.setter
    def data(self, data: Dict[str, Any]) -> None:
        """Sets the observation data set. Kindly note that the data won't be
        validated.

        Args:
            data: The data set dictionary.
        """
        self._data = data
