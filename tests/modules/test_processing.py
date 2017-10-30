#!/usr/bin/env python3.6

"""Tests the classes of the processing modules."""

__author__ = 'Philipp Engel'
__copyright__ = 'Copyright (c) 2017 Hochschule Neubrandenburg'
__license__ = 'BSD (2-Clause)'

import pytest

from testfixtures import LogCapture

from core.manager import *
from modules.processing import *


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

@pytest.fixture(scope='module')
def inspector(manager) -> ResponseValueInspector:
    """Returns a ResponseValueInspector object.

    Args:
        manager (Manager): Instance of ``core.Manager``.

    Returns:
        An instance of class ``module.processing.ResponseValueInspector``.
    """
    return ResponseValueInspector('responseValueInspector',
                                  'modules.processing.ResponseValueInspector',
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


class TestResponseValueInspector(object):
    """
    Test for the ``module.processing.ResponseValueInspector`` class.
    """

    def test_process_observation(self,
                                 inspector: ResponseValueInspector,
                                 observations: List[Observation]) -> None:
        obs = observations[1]

        obs_name = obs.get('name')
        obs_target = obs.get('target')
        response_name = 'slopeDist'

        min_val = 10.0
        max_val = 100.0

        with LogCapture() as log_capture:
            # Test 1.
            obs.data['name'] = 'test'
            inspector.process_observation(obs)

            # Test 2.
            obs.data['name'] = obs_name
            obs.data['responseSets']['slopeDist']['value'] = 'test'
            inspector.process_observation(obs)

            # Test 3.
            obs.data['responseSets']['slopeDist']['value'] = 10.0
            inspector.process_observation(obs)

            # Test 4.
            obs.data['responseSets']['slopeDist']['value'] = 0.0
            inspector.process_observation(obs)

            # Test 5.
            obs.data['responseSets']['slopeDist']['value'] = 200.0
            inspector.process_observation(obs)

            log_capture.check(
                (inspector.name, 'WARNING',  'Observation "{}" with target '
                                             '"{}" is not defined'
                                             .format('test',
                                                     obs_target)),
                (inspector.name, 'WARNING',  'Response value "{}" of '
                                             'observation "{}" with target '
                                             '"{}" is not a number'
                                             .format(response_name,
                                                     obs_name,
                                                     obs_target)),
                (inspector.name, 'DEBUG',    'Response value "{}" of '
                                             'observation "{}" with target '
                                             '"{}" is within the limits'
                                             .format(response_name,
                                                     obs_name,
                                                     obs_target)),
                (inspector.name, 'CRITICAL', 'Response value "{}" of '
                                             'observation "{}" with target '
                                             '"{}" is less than minimum '
                                             '({} < {})'
                                             .format(response_name,
                                                     obs_name,
                                                     obs_target,
                                                     0.0,
                                                     min_val)),
                (inspector.name, 'CRITICAL', 'Response value "{}" of '
                                             'observation "{}" with target '
                                             '"{}" is greater than maximum '
                                             '({} > {})'
                                             .format(response_name,
                                                     obs_name,
                                                     obs_target,
                                                     200.0,
                                                     max_val))
            )

    def test_is_number(self, inspector: ResponseValueInspector) -> None:
        assert inspector.is_number('10') is True
        assert inspector.is_number('10.5') is True
        assert inspector.is_number('foo') is False
