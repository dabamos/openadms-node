#!/usr/bin/env python3.6


"""Tests the OpenADMS the classes of the processing module."""

__author__ = 'Philipp Engel'
__copyright__ = 'Copyright (c) 2017 Hochschule Neubrandenburg'
__license__ = 'EUPL'

import pytest
import uuid

from module.processing import *
from core.observation import Observation


data = {
    'id': Observation.get_new_id(),
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
