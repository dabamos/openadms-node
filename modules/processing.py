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
    Extracts values from the raw responses of a given observation set and
    converts them to the defined types.
    """

    def __init__(self, name, config_manager, sensor_manager):
        Prototype.__init__(self, name, config_manager, sensor_manager)

    def action(self, obs):
        """Extracts the values from the raw responses of the observation
        using regular expressions."""
        response = obs.get('Response')
        response_pattern = obs.get('ResponsePattern')

        if not response or response == '':
            logger.warning('No response in observation "{}"'
                           .format(obs.get('Name')))
            return obs

        pattern = re.compile(response_pattern)
        matches = pattern.match(response)

        if not matches:
            logger.error('Response "{}" of observation "{}" with ID "{}" from '
                         'sensor "{}" on port "{}" does not match extraction '
                         'pattern'.format(self.sanitize(response),
                                          obs.get('Name'),
                                          obs.get('SensorName'),
                                          obs.get('PortName')))
            return obs

        # The regular expression pattern needs a least one defined group
        # by using the braces "(" and ")". Otherwise, the extraction of the
        # values fails.
        #
        # Right: "(.*)"
        # Wrong: ".*"
        response_sets = obs.get('ResponseSets')

        if pattern.groups == 0:
            logger.error('No group(s) defined in regular expression pattern of '
                         'observation "{}" with ID "{}"'.format(obs.get('Name'),
                                                                obs.get('ID')))
            return obs

        if pattern.groups != len(response_sets):
            logger.warning('Number of responses ({}) mismatch number of '
                           'defined response sets ({}) of observation "{}" '
                           'with ID "{}"'.format(pattern.groups,
                                                 len(response_sets),
                                                 obs.get('Name'),
                                                 obs.get('ID')))
            return obs

        # Convert the type of the parsed raw values from string to the actual
        # data type.
        for response_name, response_set in response_sets.items():
            raw_value = matches.group(response_name)

            if not raw_value:
                logger.warning('No raw value "{}" in observation "{}" '
                               'with ID "{}"'.format(response_name,
                                                     obs.get('Name'),
                                                     obs.get('ID')))
                return obs

            logger.debug('Extracted "{}" from raw response of observation "{}" '
                         'with ID "{}"'.format(raw_value,
                                               obs.get('Name'),
                                               obs.get('ID')))

            response_type = response_set.get('Type').lower()
            response_value = None

            # Convert raw value to float.
            if response_type == 'float':
                # Replace comma by dot.
                dot_value = raw_value.replace(',', '.')

                if self.is_float(dot_value):
                    response_value = float(dot_value)
                    logger.debug('Converted raw value "{}" to '
                                 'float value "{}"'.format(response_value,
                                                           response_value))
                else:
                    logger.warning('Value "{}" could not be converted '
                                   '(not float)'.format(response_value))
            # Convert raw value to int.
            elif response_type == 'integer':
                if self.is_int(raw_value):
                    response_value = int(raw_value)
                    logger.debug('Converted raw value "{}" to integer '
                                 'value "{}"'.format(raw_value,
                                                     response_value))
                else:
                    logger.warning('Value "{}" could not be converted '
                                   '(not integer)'.format(raw_value))
            # "Convert" raw value to string.
            else:
                response_value = raw_value

            response_set['Value'] = response_value

        return obs

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


class ReturnCodeInspector(Prototype):

    """
    Inspects the return code in an observation sent by sensors of Leica
    Geosystems and creates an appropriate log message.
    """

    def __init__(self, name, config_manager, sensor_manager):
        Prototype.__init__(self, name, config_manager, sensor_manager)
        """
        The dictionary has the following format:

            {
                return code number: [ log level, log message ]
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
        self.code_descriptions = {
               5: [4, 'GeoCOM command unknown'],
             514: [4, 'Several targets detected'],
            1285: [4, 'Only angle measurement valid'],
            1292: [4, 'Distance measurement not done (no aim, etc.)'],
            8710: [4, 'No target detected']
        }

    def action(self, obs):
        return_code = obs.validate('ResponseSets', 'ReturnCode', 'Value')

        if return_code is None:
            logger.warning('No return code in observation "{}" '
                           'with ID "{}"'.format(obs.get('Name'),
                                                 obs.get('ID')))
            return obs

        if return_code == 0:
            logger.debug('Observation "{}" with ID "{}" was successful '
                        '(code "{}")'.format(obs.get('Name'),
                                             obs.get('ID'),
                                             return_code))
            return obs

        # Get level and error message of the return code.
        lvl = msg = None

        if self.code_descriptions.get(return_code):
            lvl, msg = self.code_descriptions.get(return_code)

        if lvl and msg:
            # Return code related log message.
            logger.log(lvl * 10, 'Observation "{}" with ID "{}": {} '
                                 '(code "{}")'.format(obs.get('Name'),
                                                      obs.get('ID'),
                                                      msg,
                                                      return_code))
        else:
            # Generic log message.
            logger.error('Error occurred on observation "{}" (code "{}")'
                         .format(obs.get('Name'), return_code))

        return obs
