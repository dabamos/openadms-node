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

"""Tests the OpenADMS the classes of the totalstation module."""

__author__ = 'Philipp Engel'
__copyright__ = 'Copyright (c) 2017 Hochschule Neubrandenburg'
__license__ = 'EUPL'

import pytest
import uuid

from module.totalstation import *
from core.observation import Observation


data = {
    'id': str(uuid.uuid4()),
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


class TestDistanceCorrector:

    def setup(self):
        pass

    def test_get_atmospheric_correction(self):
        t = [-12.48, 0.35, 12.0, 26.6, 38.7]
        p = [1000.78, 1005.45, 1013.3, 1011.25, 990.0]
        h = [0.998, 0.9575, 0.8, 0.5531, 0.129]

        results = [-23.2859, -10.1367, -0.2421, 14.2711, 30.3193]

        for i in range(len(results)):
            a = DistanceCorrector.get_atmospheric_correction(t[i], p[i], h[i])
            r = round(a, 4)

            assert r == results[i]
