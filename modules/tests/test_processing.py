#!/usr/bin/env python3.6

"""Tests the OpenADMS the classes of the processing modules."""

__author__ = 'Philipp Engel'
__copyright__ = 'Copyright (c) 2017 Hochschule Neubrandenburg'
__license__ = 'BSD (2-Clause)'

import pytest

from core.manager import *
from modules.processing import *


@pytest.fixture(scope='modules')
def my_observation() -> Iterable[Any]:
    file_path = Path('tests/data/observations.json')

    with open(file_path) as fh:
        data = json.loads(fh.read())

    return [Observation(n) for n in data]


class TestPreProcessor(object):

    def test_process_observation(self, my_observation):
        PreProcessor.process_observation(my_observation)
