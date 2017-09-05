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

"""Tests the OpenADMS the classes of the processing module."""

__author__ = 'Philipp Engel'
__copyright__ = 'Copyright (c) 2017 Hochschule Neubrandenburg'
__license__ = 'EUPL'

import pytest
import uuid

from module.processing import *
from core.observation import Observation


data = {
    'id': Observation.get_id(),
    'target': 'test',
    'requestSets': {
        'getValue': {
            'response': '+0025.9\r',
            'responsePattern': '(?P<temperature>[+-]?\\d+\\.+\\d)'
        }
    },
    'responseSets': {
        'temperature': {
            'type': 'float',
            'unit': 'C'
        }
    }
}


class TestPreProcessor:

    def setup(self):
        pass

    def test_process_observation(self):
        obs = Observation(data)
        obj = PreProcessor('Test', None, None)
        result = obj.process_observation(obs)
        t = result.get('responseSets').get('temperature').get('value')
        assert t == 25.9
