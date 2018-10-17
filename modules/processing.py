#!/usr/bin/env python3.6

"""Module for data processing (pre-processing, atmospheric corrections,
transformations, and so on)."""

__author__ = 'Philipp Engel'
__copyright__ = 'Copyright (c) 2017 Hochschule Neubrandenburg'
__license__ = 'BSD-2-Clause'

import re

from typing import Union

from core.observation import Observation
from core.manager import Manager
from core.prototype import Prototype


class PreProcessor(Prototype):
    """
    PreProcessor extracts values from the raw responses of a given observation
    and converts them to the defined data types.

    This module has nothing to configure.
    """

    def __init__(self, module_name: str, module_type: str, manager: Manager):
        super().__init__(module_name, module_type, manager)

    def process_observation(self, obs: Observation) -> Observation:
        """Extracts the values from the raw responses of the observation
        using regular expressions.

        Args:
            obs: The observation object.

        Returns:
            The observation object with extracted and converted responses.
        """
        for set_name, request_set in obs.get('requestSets').items():
            if not request_set.get('enabled'):
                # Request is disabled.
                continue

            if set_name not in obs.get('requestsOrder'):
                # Request should be ignored.
                continue

            response = request_set.get('response')
            response_pattern = request_set.get('responsePattern')

            if response is None or len(response) == 0:
                self.logger.warning(f'No response "{set_name}" in observation '
                                    f'"{obs.get("name")}" of target '
                                    f'"{obs.get("target")}" from sensor '
                                    f'"{obs.get("sensorName")}" on port '
                                    f'"{obs.get("portName")}"')
                continue

            try:
                pattern = re.compile(response_pattern)
                match = pattern.search(response)
            except Exception:
                self.logger.error(f'Invalid regular expression for response '
                                  f'"{set_name}" in observation '
                                  f'"{obs.get("name")}" of target '
                                  f'"{obs.get("target")}" from sensor '
                                  f'"{obs.get("sensorName")}" on port '
                                  f'"{obs.get("portName")}"')
                return obs

            if not match:
                self.logger.error(f'Response "{self.sanitize(response)}" of '
                                  f'request "{set_name}" in observation '
                                  f'"{obs.get("name")}" of target '
                                  f'"{obs.get("target")}" from sensor '
                                  f'"{obs.get("sensorName")}" on port '
                                  f'"{obs.get("portName")}" does not match '
                                  f'extraction pattern')
                return obs

            # The regular expression pattern needs at least one named group
            # defined. Otherwise, the extraction of the values fails.
            #
            # Right: "(?P<id>.*)"
            # Wrong: ".*"
            if pattern.groups == 0:
                self.logger.error(f'No group(s) defined in regular expression '
                                  f'pattern of observation "{obs.get("name")}" '
                                  f'of target "{obs.get("target")}"')
                return obs

            # Convert the type of the parsed raw values from string to the
            # actual data type (float, int).
            response_sets = obs.get('responseSets')

            for group_name, raw_value in match.groupdict("").items():
                if raw_value is None or len(raw_value) == 0:
                    self.logger.error(f'Undefined raw value in response set '
                                      f'"{group_name}" in observation '
                                      f'"{obs.get("name")}" of target '
                                      f'"{ obs.get("target")}"')
                    continue

                response_set = response_sets.get(group_name)

                if not response_set:
                    self.logger.error(f'Undefined response set "{group_name}" '
                                      f'in observation "{obs.get("name")}" '
                                      f'of target "{obs.get("target")}"')
                    continue

                response_type = response_set.get('type').lower()

                if response_type == 'float':
                    # Convert raw value to float. Replace comma by dot.
                    response_value = self.to_float(raw_value)
                elif response_type == 'integer':
                    # Convert raw value to int.
                    response_value = self.to_int(raw_value)
                else:
                    response_value = raw_value

                if response_value is not None:
                    self.logger.debug(f'Extracted "{response_value}" from raw '
                                      f'response "{group_name}" in observation '
                                      f'"{ obs.get("name")}" of target '
                                      f'"{obs.get("target")}"')
                    response_set['value'] = response_value

        return obs

    def is_int(self, value: str) -> bool:
        """Returns whether a value is int or not. Float values are seen as int.

        Args:
            value: The value string.

        Returns:
            True if value is integer, false if not.
        """
        try:
            int(value)
            return True
        except ValueError:
            return False

    def is_float(self, value: str) -> bool:
        """Returns whether a value is float or not.

        Args:
            value: The value string.

        Returns:
            True if value is float, false if not.
        """
        try:
            float(value)
            return True
        except ValueError:
            return False

    def sanitize(self, s: str) -> str:
        """Escapes some non-printable characters in a given string.

        Args:
            s: String to sanitize.

        Returns:
            Sanitized string.
        """
        return s.replace('\n', '\\n')\
                .replace('\r', '\\r')\
                .replace('\t', '\\t')

    def to_float(self, raw_value: str) -> Union[float, None]:
        """Converts string to float.

        Args:
            raw_value: The raw string.

        Returns:
            Float number if string can be converted, otherwise None.
        """
        dot_value = raw_value.replace(',', '.')

        if self.is_float(dot_value):
            response_value = float(dot_value)
            return response_value
        else:
            self.logger.warning(f'Value "{raw_value}" could not be converted '
                                f'(invalid float)')
            return None

    def to_int(self, raw_value: str) -> Union[int, None]:
        """Converts string to int.

        Args:
            raw_value: The raw string.

        Returns:
            Integer number if string can be converted, otherwise None.
        """
        if self.is_int(raw_value):
            response_value = int(raw_value)
            return response_value
        else:
            self.logger.warning(f'Value "{raw_value}" could not be converted '
                                f'(invalid integer)')
            return None


class ResponseValueInspector(Prototype):
    """
    ResponseValueInspector checks if response values of observations are within
    defined thresholds and creates critical log messages if not.

    The JSON-based configuration for this module:

    Parameters:
        observations (Dict): Observations to inspect.

    Example:
        The configuration may be::

            {
                "observations": {
                    "getDistance": {
                        "slopeDist": {
                            "min": 2.0,
                            "max": 300.0
                        }
                    }
                }
            }
    """

    def __init__(self, module_name: str, module_type: str, manager: Manager):
        super().__init__(module_name, module_type, manager)
        config = self.get_module_config(self._name)
        self._observations = config.get('observations', {})

    def process_observation(self, obs: Observation) -> Observation:
        """Checks, if responses are inside defined bounds.

        Args:
            obs: The observation object.

        Returns:
            The untouched observation object.
        """
        if not obs.get('name') in self._observations:
            self.logger.warning(f'Undefined observation "{obs.get("name")}" '
                                f'with target "{obs.get("target")}"')
            return obs

        response_sets = self._observations.get(obs.get('name'))

        for response_name, limits in response_sets.items():
            response_value = obs.get_response_value(response_name)

            if response_value is None or not self.is_number(response_value):
                self.logger.warning(f'Response value "{response_name}" in '
                                    f'observation "{obs.get("name")}" '
                                    f'of target "{obs.get("target")}" is '
                                    f'not a number')
                continue

            min_value = limits.get('min')
            max_value = limits.get('max')

            if min_value <= response_value <= max_value:
                self.logger.debug(f'Response value "{response_name}" in '
                                  f'observation "{obs.get("name")}" with '
                                  f'target "{obs.get("target")}" is within '
                                  f'set limits')
            elif response_value < min_value:
                self.logger.critical(f'Response value "{response_name}" of '
                                     f'observation "{obs.get("name")}" with '
                                     f'target "{obs.get("target")}" is less '
                                     f'than minimum ({response_value} < '
                                     f'{min_value})')
            elif response_value > max_value:
                self.logger.critical(f'Response value "{response_name}" of '
                                     f'observation "{obs.get("name")}" with '
                                     f'target "{obs.get("target")}" is greater '
                                     f'than maximum ({response_value} > '
                                     f'{max_value})')

        return obs

    def is_number(self, value: str) -> bool:
        """Returns whether a value is a number or not.

        Args:
            value: The value variable.

        Returns:
            True of value is a number, false if not.
        """
        try:
            float(value)
            return True
        except ValueError:
            return False


class ReturnCodes(object):
    """
    ReturnCodes stores a dictionary of return codes of sensors of Leica
    Geosystems. The dictionary is static and has the following structure::

        {
            <return_code>: [
                <log_level> (int),
                <retry_measurement> (bool),
                <log_message> (str)
            ]
        }

    The return code numbers and messages are take from the official GeoCOM
    reference manual of the Leica TPS1200, TS30, and TM30 total stations. The
    log level can be set to these values::

        5: CRITICAL,
        4: ERROR,
        3: WARNING,
        2: INFO,
        1: DEBUG,
        0: NONE.

    Please choose a proper value for each return code. Please be aware that the
    code list is not complete yet.
    """
    codes = {
        2:    [4, False, 'Unknown error, result unspecified'],
        3:    [3, False, 'Invalid result'],
        4:    [4, False, 'Fatal error'],
        5:    [4, False, 'GeoCOM command unknown (not implemented yet)'],
        6:    [4, False, 'Function execution timed out (result unspecified)'],
        13:   [4, True,  'System busy'],
        514:  [4, False, 'Several targets detected'],
        1283: [3, False, 'Measurement without full correction'],
        1284: [3, False, 'Accuracy can not be guaranteed'],
        1285: [4, True,  'Only angle measurement valid'],
        1288: [3, False, 'Only angle measurement valid, but without full '
                         'correction'],
        1292: [4, True,  'Distance measurement not done (no aim, etc.)'],
        8704: [4, True,  'Position not reached'],
        8708: [4, True,  'Position not exactly reached'],
        8710: [4, True,  'No target detected'],
        8711: [4, False, 'Multiple targets detected'],
        8714: [4, False, 'Target acquisition not enabled'],
        8716: [4, True,  'Target position not exactly reached'],
    }


class ReturnCodeInspector(Prototype):
    """
    ReturnCodeInspector inspects the return code in an observation sent by
    sensors of Leica Geosystems and creates an appropriate log message.

    The JSON-based configuration for this module:

    Parameters:
        responseSets (List): Names of response sets to inspect.
        retries (int): Number of retries in case of an error.
    """

    def __init__(self, module_name: str, module_type: str, manager: Manager):
        super().__init__(module_name, module_type, manager)
        config = self.get_module_config(self._name)

        self._response_sets = config.get('responseSets')
        self._retries = config.get('retries')

    def process_observation(self, obs: Observation) -> Observation:
        for response_set in self._response_sets:
            return_code = obs.get_value('responseSets', response_set, 'value')

            if return_code is None:
                continue

            if return_code == 0:
                if obs.get('corrupted') is True:
                    obs.set('corrupted', False)

                continue

            # Get error message of the return code.
            error_values = ReturnCodes.codes.get(return_code)
            attempts = obs.get('attempts', 0)

            # Retry measurement.
            if error_values and attempts < self._retries:
                obs.set('attempts', attempts + 1)
                obs.set('corrupted', False)
                obs.set('nextReceiver', 0)

                self.logger.info(f'Retrying observation "{obs.get("name")}" of '
                                 f'target "{obs.get("target")}" due to return '
                                 f'code {return_code} of response '
                                 f'"{response_set}" (attempt {attempts + 1,} '
                                 f'of {self._retries})')
            else:
                obs.set('corrupted', True)

                if error_values:
                    # Return code related log message.
                    lvl, retry, msg = error_values

                    self.logger.log(lvl * 10,
                                    f'Observation "{obs.get("name")}" of '
                                    f'target "{obs.get("target")}": {msg} '
                                    f'(code {return_code} in response '
                                    f'"{response_set}")')

                else:
                    # Generic log message.
                    self.logger.error(f'Error occurred on observation '
                                      f'"{obs.get("name")}" (unknown code '
                                      f'{return_code} in response '
                                      f'"{response_set}")')
            return obs

        return obs


class UnitConverter(Prototype):
    """
    UnitConverter can be used to convert response values of arbitrary
    observations. For instance, a response in centimeters can be converted to
    meters by setting a scale factor.

    The JSON-based configuration for this module:

    Parameters:
        <responseSetName> (Dict): Responses to convert.

    Example:
        The configuration may be::

            {
                "slopeDist": {
                    "conversionType": "scale",
                    "sourceUnit": "mm",
                    "scalingValue": 0.01,
                    "targetUnit": "m"
                }
            }
    """

    def __init__(self, module_name: str, module_type: str, manager: Manager):
        super().__init__(module_name, module_type, manager)
        self._config = self._config_manager.get(self._name)

    def process_observation(self, obs: Observation) -> Observation:
        for name, properties in self._config.items():
            response_set = obs.get('responseSets').get(name)

            if not response_set:
                continue

            source_value = response_set.get('value')
            source_unit = response_set.get('unit')

            if not source_value or not source_unit:
                continue

            if source_unit != properties.get('sourceUnit'):
                self.logger.warning(f'Unit "{source_unit}" of response '
                                    f'"{name}" of observation '
                                    f'"{obs.get("name")}" of target '
                                    f'"{obs.get("target")}" does not match '
                                    f'"{properties.get("sourceUnit")}"')
                continue

            if properties.get('conversionType') == 'scale':
                target_value = self.scale(float(source_value),
                                          properties.get('scalingValue'))
                target_unit = properties.get('targetUnit')

                self.logger.info('Converted response "{}" of observation "{}" '
                                 'of target "{}" from {:.4f} {} to {:.4f} {}'
                                 .format(name,
                                         obs.get("name"),
                                         obs.get("target"),
                                         source_value,
                                         source_unit,
                                         target_value,
                                         target_unit))

                response_set = Observation.create_response_set(
                    'float',
                    target_unit,
                    round(target_value, 5))

                obs.data['responseSets'][name] = response_set

        return obs

    def scale(self, value: float, factor: float) -> float:
        """Scales value by factor.

        Args:
            value: Value to scale.
            factor: Scaling factor.

        Returns:
            Scaled value.
        """
        return value * factor
