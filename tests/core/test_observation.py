#!/usr/bin/env python3.6

"""Tests the classes of the processing modules."""

__author__ = 'Philipp Engel'
__copyright__ = 'Copyright (c) 2017 Hochschule Neubrandenburg'
__license__ = 'BSD-2-Clause'

import pytest

from core.observation import Observation


@pytest.fixture(scope='module')
def observation() -> Observation:
    return Observation()


class TestObservation():

    def test_create_response_test(self, observation: Observation) -> None:
        response_set = observation.create_response_set('test', 'none', 0.0)
        assert response_set == {'type': 'test', 'unit': 'none', 'value': 0.0}
