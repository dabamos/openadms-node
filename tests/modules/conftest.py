#!/usr/bin/env python3.6

"""Shared fixture functions for pytest."""

__author__ = 'Philipp Engel'
__copyright__ = 'Copyright (c) 2017 Hochschule Neubrandenburg'
__license__ = 'BSD-2-Clause'

import pytest

from core.manager import *
from core.observation import *


@pytest.fixture(scope='module')
def observations() -> List[Observation]:
    """Returns a List with examples observation objects.

    Returns:
        List of examples observations.
    """
    file_path = Path('tests/data/observations.json')

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
    manager.schema_manager = SchemaManager()
    manager.config_manager = ConfigManager('tests/config/config.json',
                                           manager.schema_manager)
    return manager
