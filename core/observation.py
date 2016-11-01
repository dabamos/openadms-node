#!/usr/bin/env python3
"""
Copyright (c) 2016 Hochschule Neubrandenburg.

Licensed under the EUPL, Version 1.1 or - as soon they will be approved
by the European Commission - subsequent versions of the EUPL (the
"Licence");

You may not use this work except in compliance with the Licence.

You may obtain a copy of the Licence at:

    http://ec.europa.eu/idabc/eupl

Unless required by applicable law or agreed to in writing, software
distributed under the Licence is distributed on an "AS IS" basis,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the Licence for the specific language governing permissions and
limitations under the Licence.
"""

import json
import logging

logger = logging.getLogger('openadms')


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
                'id': None,
                'name': None,
                'nextReceiver': 0,
                'portName': None,
                'receivers': [],
                'response': None,
                'responseSets': {},
                'timeStamp': None
            }
        else:
            self._data = data

    @property
    def data(self):
        return self._data

    @data.setter
    def data(self, data):
        """Sets the observation data set. Kindly note that the data won't be
        validated.

        Args:
            data (Dict): The data set dictionary.
        """
        self._data = data

    def get(self, key, default=None):
        """Returns the value to a given key.

        Args:
            key (str): The key of the value.
            default: Default return value.

        Returns:
            Returns a value from the observation data.
        """
        return self._data.get(key, default)

    def get_value(self, *args):
        """Returns the value of a set of keys.

        Args:
            *args (str): The keys.

        Returns:
            Returns a value from the observation data.
        """
        ref = self.data

        for x in args:
            try:
                ref = ref.get(x)
            except AttributeError:
                # logger.info('No "{}" in observation "{}" with ID "{}"'
                #             .format('->'.join(args),
                #                     self.get('Name'),
                #                     self.get('ID')))
                return

        return ref

    def set(self, key, value):
        """Sets key and value in the data set.

        Args:
            key (str): The key of the data set value.
            value: The data set value.
        """
        self._data[key] = value

    def to_json(self):
        """Returns a dump of the data set in JSON format.

        Returns:
            str: Data in JSON format.
        """
        return json.dumps(self._data)
