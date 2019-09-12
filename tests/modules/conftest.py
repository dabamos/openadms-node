#!/usr/bin/env python3

"""Shared fixture functions for pytest."""

__author__ = 'Philipp Engel'
__copyright__ = 'Copyright (c) 2017 Hochschule Neubrandenburg'
__license__ = 'BSD-2-Clause'

import json

from typing import List

import pytest

from core.manager import (ConfigManager, Manager, SchemaManager)
from core.observation import Observation


@pytest.fixture(scope='module')
def observations() -> List[Observation]:
    """Returns a List with examples observation objects.

    Returns:
        List of examples observations.
    """
    file_path = 'tests/data/observations.json'

    with open(file_path) as fh:
        data = json.loads(fh.read())

    return [Observation(n) for n in data]


@pytest.fixture(scope='module')
def manager() -> Manager:
    """Returns a Manager object.

    Returns:
        An instance of class ``core.Manager``.
    """
    manager = Manager()
    manager.schema = SchemaManager()
    manager.config = ConfigManager('tests/config/config.json',
                                   manager.schema)
    return manager
