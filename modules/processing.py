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
import math
import re
import time

from modules import prototype

"""Module for data processing (pre-precessing, atmospheric corrections,
transformations)."""

logger = logging.getLogger('openadms')


class PreProcessor(prototype.Prototype):

    """Extracts values from the raw responses of a given observation set
    and converts them to the defined types.
    """

    def __init__(self, name, config_manager):
        prototype.Prototype.__init__(self, name, config_manager)

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
        parsed = pattern.search(response)

        if not parsed:
            logger.error('Response "{}" of observation "{}" from sensor "{}" '
                         'on port "{}" does not match extraction pattern'
                         .format(self._sanitize(response),
                                 obs.get('Name'),
                                 obs.get('SensorName'),
                                 obs.get('PortName')))
            return obs

        # The regular expression pattern needs a least one defined group
        # by using the braces "(" and ")". Otherwise, an extraction of the
        # values fails.
        #
        # Right: "(.*)"
        # Wrong: ".*"
        raw_responses = parsed.groups()
        response_sets = obs.get('ResponseSets')

        if len(raw_responses) == 0:
            logger.error('No group(s) defined in regular expression pattern')
            return obs

        if len(raw_responses) != len(response_sets):
            logger.warning('Number of responses mismatch number of defined '
                           'response sets of observation "{}"'
                           .format(obs.get('Name')))
            return obs

        # Convert the type of the parsed raw values from string to the actual
        # data type.
        for raw_response, response_set in zip(raw_responses, response_sets):
            if not (raw_response and response_set):
                logger.error('Extraction of raw response of observation "{}" '
                             'failed'.format(obs.get('Name')))
                return obs

            logger.debug('Extracted "{}" from raw response of observation "{}"'
                         .format(raw_response, obs.get('Name')))

            response_type = response_set.get('Type').lower()
            response_value = None

            # Convert raw value to float.
            if response_type == 'float':
                # Replace comma by dot.
                dot_response = raw_response.replace(',', '.')

                if self._is_float(dot_response):
                    response_value = float(dot_response)

                    logger.debug('Converted raw value "{}" to '
                                 'float value "{}"'.format(raw_response,
                                                           response_value))
                else:
                    logger.warning('Value "{}" could not be converted '
                                   '(not float)'.format(raw_response))
            # Convert raw value to int.
            elif response_type == 'integer':
                if self._is_int(raw_response):
                    response_value = int(raw_response)

                    logger.debug('Converted raw value "{}" to integer '
                                 'value "{}"'.format(raw_response,
                                                     response_value))
                else:
                    logger.warning('Value "{}" couldn\'t be converted '
                                   '(not integer)'.format(raw_response))
            # Convert raw value to string.
            else:
                # Well, in this case (input == output) do nothing.
                continue

            response_set['Value'] = response_value

        return obs

    def destroy(self, *args):
        pass

    def _is_int(self, value):
        """Returns whether a value is int or not."""
        try:
            int(value)
            return True
        except ValueError:
            return False

    def _is_float(self, value):
        """Returns whether a value is float or not."""
        try:
            float(value)
            return True
        except ValueError:
            return False

    def _sanitize(self, s):
        """Removes some non-printable characters from a string."""
        sanitized = s.replace('\n', '\\n') \
                     .replace('\r', '\\r') \
                     .replace('\t', '\\t')

        return sanitized


class ReturnCodeInspector(prototype.Prototype):

    """
    Inspects the return code in observation sent by sensors of Leica
    Geosystems.
    """

    def __init__(self, name, config_manager):
        prototype.Prototype.__init__(self, name, config_manager)
        # config = self._config_manager.config[self._name]

    def action(self, obs):
        return_codes = obs.find('ResponseSets', 'Description', 'ReturnCode')
        return_code = None

        if len(return_codes) > 0:
            return_code = return_codes[0].get('Value')
        else:
            logger.warning('ReturnCode is missing in observation "{}"'
                           .format(obs.get('Name')))
            return obs

        if return_code == 0:
            logger.info('Observation "{}" was successful (code "{}")'
                        .format(obs.get('Name'), return_code))
        else:
            logger.warning('Error occured on observation "{}" (code "{}")'
                           .format(obs.get('Name'), return_code))

        return obs

    def destroy(self, *args):
        pass
