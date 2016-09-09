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

import pytest

from modules.processing import *
from core.observation import Observation

"""Tests the OpenADMS processing modules."""

data = { 'ID': 'Test', 'Response': '+0025.9\r', 'ResponsePattern': '(?P<Temperature>[+-]?\\d+\\.+\\d)', 'ResponseSets': { 'Temperature': { 'Type': 'Float', 'Unit': 'C' } } }

class TestPreProcessor():

    def setup(self):
        pass

    def test_action(self):
        obs = Observation(data)
        obj = PreProcessor('Test', None, None)
        result = obj.action(obs)
        t = result.get('ResponseSets').get('Temperature').get('Value')
        assert t == 25.9