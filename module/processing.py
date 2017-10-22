#!/usr/bin/env python3.6

"""Module for data processing (pre-processing, atmospheric corrections,
transformations, and so on)."""

__author__ = 'Philipp Engel'
__copyright__ = 'Copyright (c) 2017 Hochschule Neubrandenburg'
__license__ = 'BSD (2-Clause)'

import re

from typing import *

from core.observation import Observation
from core.manager import Manager
from module.prototype import Prototype


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
                self.logger.warning('No response "{}" in observation "{}" of '
                                    'target "{}"'.format(set_name,
                                                         obs.get('name'),
                                                         obs.get('target')))
                continue

            try:
                pattern = re.compile(response_pattern)
                match = pattern.search(response)
            except Exception:
                self.logger.error('Invalid regular expression for response '
                                  '"{}" in observation "{}" of target "{}"'
                                  .format(set_name,
                                          obs.get('name'),
                                          obs.get('target')))
                return obs

            if not match:
                self.logger.error('Response "{}" of request "{}" of '
                                  'observation "{}" of target "{}" from sensor '
                                  '"{}" on port "{}" does not match extraction '
                                  'pattern'.format(self.sanitize(response),
                                                   set_name,
                                                   obs.get('name'),
                                                   obs.get('target'),
                                                   obs.get('sensorName'),
                                                   obs.get('portName')))
                return obs

            # The regular expression pattern needs a least one named group
            # defined. Otherwise, the extraction of the values fails.
            #
            # Right: "(?P<id>.*)"
            # Wrong: ".*"
            if pattern.groups == 0:
                self.logger.error('No group(s) defined in regular expression '
                                  'pattern of observation "{}" of target "{}"'
                                  .format(obs.get('name'), obs.get('target')))
                return obs

            # Convert the type of the parsed raw values from string to the
            # actual data type (float, int).
            response_sets = obs.get('responseSets')

            for group_name, raw_value in match.groupdict("").items():
                if raw_value is None or len(raw_value) == 0:
                    self.logger.error('No raw value found in response set "{}" '
                                      'of observation "{}" of target "{}"'
                                      .format(group_name,
                                              obs.get('name'),
                                              obs.get('target')))
                    continue

                response_set = response_sets.get(group_name)

                if not response_set:
                    self.logger.error('Response set "{}" of observation "{}" '
                                      'of target "{}" not defined'
                                      .format(group_name,
                                              obs.get('name'),
                                              obs.get('target')))
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
                    self.logger.debug('Extracted "{}" from raw response "{}" '
                                      'of observation "{}" of target "{}"'
                                      .format(response_value,
                                              group_name,
                                              obs.get('name'),
                                              obs.get('target')))
                    response_set['value'] = response_value

        return obs

    def is_int(self, value: str) -> bool:
        """Returns whether a value is int or not.

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
        """Removes some non-printable characters from a string.

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
            self.logger.warning('Value "{}" could not be converted '
                                '(not float)'.format(raw_value))
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
            self.logger.warning('Value "{}" could not be converted '
                                '(not integer)'.format(raw_value))
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
        config = self.get_config(self._name)
        self._observations = config.get('observations', {})

    def process_observation(self, obs: Observation) -> Observation:
        """Checks, if responses are inside defined bounds.

        Args:
            obs: The observation object.

        Returns:
            The untouched observation object.
        """
        if not obs.get('name') in self._observations:
            # Nothing defined for this observation.
            return obs

        response_sets = self._observations.get(obs.get('name'))

        for response_name, limits in response_sets.items():
            response_value = obs.get_response_value(response_name)

            if not response_value or not self.is_number(response_value):
                continue

            min_value = limits.get('min')
            max_value = limits.get('max')

            self.logger.debug('Checking response "{}" of observation "{}" with '
                              'target "{}"'.format(response_name,
                                                   obs.get('name'),
                                                   obs.get('target')))

            if min_value and response_value < min_value:
                self.logger.critical('Response value "{}" of observation "{}" '
                                     'with target "{}" is less than minimum '
                                     '({} < {})'.format(response_name,
                                                        obs.get('name'),
                                                        obs.get('target'),
                                                        response_value,
                                                        min_value))

            if max_value and response_value > max_value:
                self.logger.critical('Response value "{}" of observation "{}" '
                                     'with target "{}" is greater than maximum '
                                     '({} > {})'.format(response_name,
                                                        obs.get('name'),
                                                        obs.get('target'),
                                                        response_value,
                                                        max_value))

        return obs

    def is_number(self, value: Any) -> bool:
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

    Please choose a proper value for each return code.
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
        config = self.get_config(self._name)

        self._response_sets = config.get('responseSets')
        self._retries = config.get('retries')

    def process_observation(self, obs: Observation) -> Observation:
        for response_set in self._response_sets:
            return_code = obs.get_value('responseSets', response_set, 'value')

            # Return code is zero or not in response set.
            if return_code is None or return_code == 0:
                continue

            # Get level and error message of the return code.
            error_values = ReturnCodes.codes.get(return_code)
            lvl, retry, msg = error_values

            attempts = obs.get('attempts', 0)

            # Retry measurement.
            if retry and attempts < self._retries:
                obs.set('attempts', attempts + 1)
                obs.set('nextReceiver', 0)
                obs.set('corrupted', False)

                self.logger.info('Retrying observation "{}" of target "{}" due '
                                 'to return code {} of response "{}" '
                                 '(attempt {} of {})'.format(obs.get('name'),
                                                             obs.get('target'),
                                                             return_code,
                                                             response_set,
                                                             attempts + 1,
                                                             self._retries))
            else:
                obs.set('corrupted', True)

                if error_values:
                    # Return code related log message.
                    self.logger.log(lvl * 10,
                                    'Observation "{}" of target "{}": {} '
                                    '(code {} in response "{}")'
                                    .format(obs.get('name'),
                                            obs.get('target'),
                                            msg,
                                            return_code,
                                            response_set))

                else:
                    # Generic log message.
                    self.logger.error('Error occurred on observation "{}" '
                                      '(code {} in response "{}")'
                                      .format(obs.get('name'),
                                              return_code,
                                              response_set))
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
                    "designatedUnit": "m"
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

            src_value = response_set.get('value')
            src_unit = response_set.get('unit')

            if not src_value or not src_unit:
                continue

            if src_unit != properties.get('sourceUnit'):
                self.logger.warning('Unit "{}" of response "{}" of observation '
                                    '"{}" of target "{}" does not match "{}"'
                                    .format(src_unit,
                                            name,
                                            obs.get('name'),
                                            obs.get('target'),
                                            properties.get('sourceUnit')))
                continue

            if properties.get('conversionType') == 'scale':
                dgn_value = self.scale(float(src_value),
                                       properties.get('scalingValue'))
                dgn_unit = properties.get('designatedUnit')

                self.logger.info('Converted response "{}" of observation "{}" '
                                 'of target "{}" from {:.4f} {} to {:.4f} {}'
                                 .format(name,
                                         obs.get('name'),
                                         obs.get('target'),
                                         src_value,
                                         src_unit,
                                         dgn_value,
                                         dgn_unit))

                response_set = Observation.create_response_set(
                    'float',
                    dgn_unit,
                    round(dgn_value, 5)
                )

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
