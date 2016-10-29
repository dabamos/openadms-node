#!/usr/bin/env python3
"""
Copyright (c) 2016 Hochschule Neubrandenburg.

Licensed under the EUPL, Version 1.1 or - as soon they will be approved
by the European Commission - subsequent versions of the EUPL (the
"Licence");

You may not use this work except in compliance with the Licence.

You may obtain a copy of the Licence at:

    http://ec.europa.eu/idabc/eupl

Unless required by applicable law or agreed to in writing, software
distributed under the Licence is distributed on an "AS IS" basis,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the Licence for the specific language governing permissions and
limitations under the Licence.
"""

import logging
import re

from modules.prototype import Prototype

"""Module for data processing (pre-precessing, atmospheric corrections,
transformations)."""

logger = logging.getLogger('openadms')


class PreProcessor(Prototype):
    """
    Extracts values from the raw response of a given observation set and
    converts them to the defined types.
    """

    def __init__(self, name, config_manager, sensor_manager):
        Prototype.__init__(self, name, config_manager, sensor_manager)

    def process_observation(self, obs):
        """Extracts the values from the raw responses of the observation
        using regular expressions."""
        for set_name, request_set in obs.get('requestSets').items():
            response = request_set.get('response')
            response_pattern = request_set.get('responsePattern')

            if response is None or response == '':
                logger.error('No response in observation "{}" with ID "{}"'
                             .format(obs.get('name'), obs.get('id')))
                return obs

            pattern = re.compile(response_pattern)
            match = pattern.search(response)

            if not match:
                logger.error('Response "{}" of request "{}" of observation '
                             '"{}" with ID "{}" from sensor "{}" on port "{}" '
                             'does not match extraction pattern'
                             .format(self.sanitize(response),
                                     set_name,
                                     obs.get('name'),
                                     obs.get('id'),
                                     obs.get('sensorName'),
                                     obs.get('portName')))
                return obs

            # The regular expression pattern needs a least one defined group
            # by using the braces "(" and ")". Otherwise, the extraction of the
            # values fails.
            #
            # Right: "(.*)"
            # Wrong: ".*"
            if pattern.groups == 0:
                logger.error('No group(s) defined in regular expression '
                             'pattern of observation "{}" with ID "{}"'
                             .format(obs.get('name'), obs.get('id')))
                return obs

            # Convert the type of the parsed raw values from string to the
            # actual data type.
            response_sets = obs.get('responseSets')

            for group_name, raw_value in match.groupdict().items():
                if not raw_value:
                    logger.error('No raw value found for response set "{}" of '
                                 'observation "{}" with ID "{}"'
                                 .format(group_name,
                                         obs.get('name'),
                                         obs.get('id')))
                    continue

                response_set = response_sets.get(group_name)

                if not response_set:
                    logger.error('Response set "{}" of observation "{}" with '
                                 'ID "{}" not defined'.format(group_name,
                                                              obs.get('name'),
                                                              obs.get('id')))
                    continue

                response_type = response_set.get('type').lower()

                # Convert raw value to float.
                if response_type == 'float':
                    # Replace comma by dot.
                    response_value = self.to_float(raw_value)
                # Convert raw value to int.
                elif response_type == 'integer':
                    response_value = self.to_int(raw_value)
                # "Convert" raw value to string.
                else:
                    response_value = raw_value

                if response_value is not None:
                    logger.debug('Extracted "{}" from raw response "{}" of '
                                 'observation "{}" with ID "{}"'
                                 .format(response_value,
                                         group_name,
                                         obs.get('name'),
                                         obs.get('id')))
                    response_set['value'] = response_value

        return obs

    def to_float(self, raw_value):
        dot_value = raw_value.replace(',', '.')

        if self.is_float(dot_value):
            response_value = float(dot_value)
            # logger.debug('Converted raw value "{}" to '
            #              'float value "{}"'.format(raw_value,
            #                                        response_value))
            return response_value
        else:
            logger.warning('Value "{}" could not be converted '
                           '(not float)'.format(raw_value))
            return None

    def to_int(self, raw_value):
        if self.is_int(raw_value):
            response_value = int(raw_value)
            # logger.debug('Converted raw value "{}" to integer '
            #              'value "{}"'.format(raw_value,
            #                                  response_value))
            return response_value
        else:
            logger.warning('Value "{}" could not be converted '
                           '(not integer)'.format(raw_value))
            return None

    def is_int(self, value):
        """Returns whether a value is int or not."""
        try:
            int(value)
            return True
        except ValueError:
            return False

    def is_float(self, value):
        """Returns whether a value is float or not."""
        try:
            float(value)
            return True
        except ValueError:
            return False

    def sanitize(self, s):
        """Removes some non-printable characters from a string."""
        sanitized = s.replace('\n', '\\n') \
                     .replace('\r', '\\r') \
                     .replace('\t', '\\t')

        return sanitized


class ReturnCodes(object):
    """
    ReturnCodes stores a dictionary of return codes of sensors of Leica
    Geosystems. The dictionary is static and has the following structure:

        {
            return code: [ log level, retry measurement, log message ]
        }

    The return code numbers and messages are take from the GeoCOM reference
    manual of the Leica TPS 1200, TS 30, and TM 30 total stations. The log
    level can be set to these values:

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
        1292: [4, True,  'Distance measurement not done (no aim, etc.)'],
        8708: [3, True,  'Position not exactly reached'],
        8710: [4, True,  'No target detected']
    }


class ReturnCodeInspector(Prototype):
    """
    ReturnCodeInspector inspects the return code in an observation sent by
    sensors of Leica Geosystems and creates an appropriate log message.
    """

    def __init__(self, name, config_manager, sensor_manager):
        Prototype.__init__(self, name, config_manager, sensor_manager)
        config = self._config_manager.config.get(self._name)

        self._keys = config.get('keys')
        self._retries = config.get('retries')

    def process_observation(self, obs):
        for key in self._keys:
            return_code = obs.get_value('responseSets', key, 'value')

            # Key is zero or not in response set.
            if return_code is None or return_code == 0:
                continue

            # Get level and error message of the return code.
            values = ReturnCodes.codes.get(return_code)

            if values:
                lvl, retry, msg = values

                # Return code related log message.
                logger.log(lvl * 10, 'Observation "{}" with ID "{}": {} '
                                     '(code "{}")'.format(obs.get('name'),
                                                          obs.get('id'),
                                                          msg,
                                                          return_code))

                # Retry measurement.
                if retry:
                    attempts = obs.get('Attempts', 0)

                    if attempts < self._retries :
                        obs.set('attempts', attempts + 1)
                        obs.set('nextReceiver', 0)
                        obs.set('corrupted', False)

                        logger.info('Retrying observation "{}" with ID "{}" '
                                    '(attempt {} of {})'
                                    .format(obs.get('name'),
                                            obs.get('id'),
                                            attempts + 1,
                                            self._retries))
                    else:
                        obs.set('corrupted', True)

                        logger.info('Maximum number of attempts ({}) reached '
                                    'for observation "{}" with ID "{}"'
                                    .format(self._retries,
                                            obs.get('name'),
                                            obs.get('id')))

                    return obs
            else:
                # Generic log message.
                logger.error('Error occurred on observation "{}" (code "{}")'
                             .format(obs.get('name'), return_code))

        return obs
