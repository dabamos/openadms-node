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

    """Extracts values from the raw responses of a given observation data set
    and converts them to the defined types.
    """

    def __init__(self, name, config_manager):
        prototype.Prototype.__init__(self, name, config_manager)

    def action(self, obs_data):
        """Extracts the values from the raw responses of the observation data
        using regular expressions."""
        response = obs_data.get('Response')
        response_pattern = obs_data.get('ResponsePattern')

        if response is None or response == '':
            logger.warning('No response in observation "{}"'
                           .format(obs_data.get('Name')))
            return obs_data

        pattern = re.compile(response_pattern)
        parsed = pattern.search(response)

        if not parsed:
            logger.error('Extraction pattern "{}" does not match response '
                         '"{}" from sensor {} on {}'
                         .format(response_pattern,
                                 self._sanitize(response),
                                 obs_data.get('SensorName'),
                                 obs_data.get('PortName')))
            return obs_data

        # The regular expression pattern needs a least one defined group
        # by using the braces "(" and ")". Otherwise, an extraction of the
        # values is not possible, which leads to an error.
        #
        # Right: "(.*)"
        # Wrong: ".*"
        raw_responses = parsed.groups()
        response_sets = obs_data.get('ResponseSets')

        if len(raw_responses) == 0:
            logger.error('No group defined in regular expression pattern')
            return obs_data

        if len(raw_responses) != len(response_sets):
            logger.warning('Number of responses mismatch number of defined '
                           'response sets of observation "{}"'
                           .format(obs_data.get('Name')))

            if len(raw_responses) > len(response_sets):
                return

        for raw_response, response_set in zip(raw_responses, response_sets):
            if raw_response is None:
                logger.error('Extraction of observation "{}" failed'
                             .format(obs_data.get('Name')))
                return obs_data

            logger.debug('Extracted "{}" from raw response of observation "{}"'
                         .format(raw_response, obs_data.get('Name')))

            response_type = response_set['Type'].lower()
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

        return obs_data

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
        san = s.replace('\n', '\\n')
        san = san.replace('\r', '\\r')
        san = san.replace('\t', '\\t')

        return san


class ReturnCodeInspector(prototype.Prototype):

    """
    Inspects the return code in observation data sent by sensors of Leica
    Geosystems.
    """

    def __init__(self, name, config_manager):
        prototype.Prototype.__init__(self, name, config_manager)
        # config = self._config_manager.config[self._name]

    def action(self, obs_data):
        response_sets = obs_data.get('ResponseSets')
        return_code = None

        if len('ResponseSets') == 0:
            logger.warning('Observation "{}" has no responses'
                           .format(obs_data.get('Name')))
            return obs_data

        for response in response_sets:
            try:
                d = response['Description'].lower()
                v = response['Value']

                if d in ['returncode', 'errorcode']:
                    return_code = v
                    break
            except KeyError:
                logger.warning('Data missing in response set of '
                               'observation "{}"'
                               .format(obs_data.get('Name')))

        if return_code is None:
            logger.debug('Return code not found in observation "{}"'
                         .format(obs_data.get('Name')))
            return obs_data

        if return_code == 0:
            logger.info('Observation "{}" was successful (code "{}")'
                        .format(obs_data.get('Name'), return_code))
        else:
            logger.warning('Error occured on observation "{}" (code "{}")'
                           .format(obs_data.get('Name'), return_code))

        return obs_data

    def destroy(self, *args):
        pass
