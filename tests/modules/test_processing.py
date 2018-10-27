#!/usr/bin/env python3.6

"""Tests the classes of the processing modules."""

__author__ = 'Philipp Engel'
__copyright__ = 'Copyright (c) 2017 Hochschule Neubrandenburg'
__license__ = 'BSD-2-Clause'

from typing import List

import pytest

from testfixtures import LogCapture

from core.observation import Observation
from modules.processing import (PreProcessor, ResponseValueInspector,
                                ReturnCodeInspector, UnitConverter)


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
def rv_inspector(manager) -> ResponseValueInspector:
    """Returns a ResponseValueInspector object.

    Args:
        manager (Manager): Instance of ``core.Manager``.

    Returns:
        An instance of class ``module.processing.ResponseValueInspector``.
    """
    return ResponseValueInspector('responseValueInspector',
                                  'modules.processing.ResponseValueInspector',
                                  manager)


@pytest.fixture(scope='module')
def rc_inspector(manager) -> ReturnCodeInspector:
    """Returns a ReturnCodeInspector object.

    Args:
        manager (Manager): Instance of ``core.Manager``.

    Returns:
        An instance of class ``module.processing.ReturnCodeInspector``.
    """
    return ReturnCodeInspector('returnCodeInspector',
                               'modules.processing.ReturnCodeInspector',
                               manager)


@pytest.fixture(scope='module')
def unit_converter(manager) -> UnitConverter:
    """Returns a UnitConverter object.

    Args:
        manager (Manager): Instance of ``core.Manager``.

    Returns:
        An instance of class ``module.processing.UnitConverter``.
    """
    return UnitConverter('unitConverter',
                         'modules.processing.UnitConverter',
                         manager)


class TestPreProcessor:
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


class TestResponseValueInspector:
    """
    Test for the ``module.processing.ResponseValueInspector`` class.
    """

    def test_process_observation(self,
                                 rv_inspector: ResponseValueInspector,
                                 observations: List[Observation]) -> None:
        """Check whether valid log messages are created."""
        obs = observations[1]

        obs_name = obs.get('name')
        obs_target = obs.get('target')
        response_name = 'slopeDist'

        min_val = 10.0
        max_val = 100.0

        valid_val = 25.0
        lt_min_val = 0.0
        gt_max_val = 200.0

        with LogCapture() as log_capture:
            # Test 1 (observation undefined).
            obs.data['name'] = 'test'
            rv_inspector.process_observation(obs)

            # Test 2 (invalid response type).
            obs.data['name'] = obs_name
            obs.data['responseSets']['slopeDist']['value'] = 'test'
            rv_inspector.process_observation(obs)

            # Test 3 (success).
            obs.data['responseSets']['slopeDist']['value'] = valid_val
            rv_inspector.process_observation(obs)

            # Test 4 (response value less than minimum).
            obs.data['responseSets']['slopeDist']['value'] = lt_min_val
            rv_inspector.process_observation(obs)

            # Test 5 (response value greater than maximum).
            obs.data['responseSets']['slopeDist']['value'] = gt_max_val
            rv_inspector.process_observation(obs)

            # Capture log messages.
            log_capture.check(
                (rv_inspector.name,
                 'WARNING',
                 f'Undefined observation "test" of target "{obs_target}"'),
                (rv_inspector.name,
                 'WARNING',
                 f'Response value "{response_name}" in observation '
                 f'"{obs_name}" of target "{obs_target}" is not a number'),
                (rv_inspector.name,
                 'DEBUG',
                 f'Response value "{response_name}" in observation '
                 f'"{obs_name}" of target "{obs_target}" is within limits'),
                (rv_inspector.name,
                 'CRITICAL',
                 f'Response value "{response_name}" in observation '
                 f'"{obs_name}" of target "{obs_target}" is less than '
                 f'minimum ({lt_min_val} < {min_val})'),
                (rv_inspector.name,
                 'CRITICAL',
                 f'Response value "{response_name}" in observation '
                 f'"{obs_name}" of target "{obs_target}" is greater than '
                 f'maximum ({gt_max_val} > {max_val})')
            )

    def test_is_number(self,
                       rv_inspector: ResponseValueInspector) -> None:
        assert rv_inspector.is_number('10') is True
        assert rv_inspector.is_number('10.5') is True
        assert rv_inspector.is_number('foo') is False


class TestReturnCodeInspector:
    """
    Test for the ``module.processing.ReturnCodeInspector`` class.
    """

    def test_process_observation(self,
                                 rc_inspector: ReturnCodeInspector,
                                 observations: List[Observation]) -> None:
        obs = rc_inspector.process_observation(observations[1])
        assert obs.data['corrupted'] is True

        obs.data['responseSets']['returnCode']['value'] = 0
        obs = rc_inspector.process_observation(obs)
        assert obs.data['corrupted'] is False
        assert obs.data['nextReceiver'] == 1


class TestUnitConverter:

    def test_process_observation(self,
                                 unit_converter: UnitConverter,
                                 observations: List[Observation]) -> None:
        pass

    def test_scale(self, unit_converter: UnitConverter) -> None:
        assert unit_converter.scale(10, 10) == 100
