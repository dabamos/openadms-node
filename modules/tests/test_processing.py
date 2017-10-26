#!/usr/bin/env python3.6

"""Tests the classes of the processing modules."""

__author__ = 'Philipp Engel'
__copyright__ = 'Copyright (c) 2017 Hochschule Neubrandenburg'
__license__ = 'BSD (2-Clause)'

import pytest

from core.manager import *
from modules.processing import *


@pytest.fixture(scope='module')
def observations() -> Iterable[Any]:
    """Returns a Dict or List with example observations.

    Returns:
        Example observations.
    """
    file_path = Path('modules/tests/data/observations.json')

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
    manager.config_manager = ConfigManager('modules/tests/data/config.json',
                                           manager.schema_manager)
    return manager


@pytest.fixture(scope='module')
def pre_processor(manager) -> PreProcessor:
    """Returns a PreProcessor object.

    Args:
        manager (Manager): Instance of ``core.Manager``.

    Returns:
        An instance of class ``module.processing.PreProcessor``.
    """
    return PreProcessor('preProcessor',
                        'modules.processing.PreProcessor',
                        manager)


class TestPreProcessor(object):
    """
    Test for the ``module.processing.PreProcessor`` class.
    """

    def test_process_observation(self,
                                 pre_processor: PreProcessor,
                                 observations: List[Observation]) -> None:
        """Tests the processing of observations."""
        obs_in = observations[0]
        obs_out = pre_processor.process_observation(obs_in)

        assert obs_out.get_response_value('temperature') == 23.1
        assert obs_out.get_response_value('pressure') == 1011.3

    def test_is_float(self, pre_processor: PreProcessor) -> None:
        assert pre_processor.is_float('10.5') is True
        assert pre_processor.is_float('foo') is False

    def test_is_int(self, pre_processor: PreProcessor) -> None:
        assert pre_processor.is_float('10') is True
        assert pre_processor.is_float('10.5') is True
        assert pre_processor.is_float('foo') is False

    def test_sanitize(self, pre_processor: PreProcessor) -> None:
        assert pre_processor.sanitize('\n\r\t') == '\\n\\r\\t'

    def test_to_float(self, pre_processor: PreProcessor) -> None:
        assert pre_processor.to_float('10,5') == 10.5
        assert pre_processor.to_float('0.9995') == 0.9995
        assert pre_processor.to_float('foo') is None

    def test_to_int(self, pre_processor: PreProcessor) -> None:
        assert pre_processor.to_int('10') == 10
        assert pre_processor.to_int('10.5') is None
        assert pre_processor.to_int('foo') is None
