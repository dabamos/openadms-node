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

import coloredlogs
import copy
import json
import logging
import logging.handlers
import math
import optparse
import os
import re
import sys

"""
Target generator for NetADMS. FOR TESTING ONLY. Reads a CSV file with targets
and a JSON file with observations/commands to merge them into a valid sensor
configuration. This tool will be deprecated in near future, once the user
interface has been finished.

"""

def grad2rad(angle):
    return angle * (math.pi / 200)

def main(t_file, c_file, o_file):
    # Load targets file.
    if not os.path.exists(t_file):
        logger.error('Targets file {} not found'.format(t_file))
        return

    targets = tuple(open(t_file, 'r'))
    logger.debug('Opened targets file {}'.format(t_file))

    # Load commands file.
    if not os.path.exists(c_file):
        logger.error('Commands file {} not found'.format(c_file))
        return

    with open(c_file) as f:
        commands = json.loads(f.read())

    logger.debug('Opened commands file {}'.format(t_file))

    result = { 'Observations': {} }

    for target in targets:
        t_id, t_hz, t_v = target.strip('\n').split(',')
        logger.debug('ID: {:>5}, Hz [gon]: {:>10}, V [gon]: {:>10}'.format(t_id,
                                                                           t_hz,
                                                                           t_v))
        hz_rad = str(round(grad2rad(float(t_hz)), 5))
        v_rad = str(round(grad2rad(float(t_v)), 5))

        logger.debug('ID: {:>5}, Hz [rad]: {:>10}, V [rad]: {:>10}'.format(t_id,
                                                                           hz_rad,
                                                                           v_rad))

        result['Observations'][str(t_id)] = []
        index = 0

        for c in commands:
            result['Observations'][str(t_id)].append(copy.deepcopy(c))
            obs_data = result['Observations'][str(t_id)][index]

            if obs_data['ID'] != None:
                obs_data['ID'] = obs_data['ID'].replace('[% id %]', t_id)

            obs_data['Request'] = obs_data['Request'].replace('[% hz %]', hz_rad)
            obs_data['Request'] = obs_data['Request'].replace('[% v %]', v_rad)

            index = index + 1

    output = json.dumps(result, sort_keys=True, indent=4, separators=(',', ': '))

    with open(o_file, 'w') as f:
        f.write(output)
        logger.debug('Saved processed commands to {}'.format(o_file))

if __name__ == '__main__':
    optparse.OptionParser.format_epilog = lambda self, formatter: self.epilog
    parser = optparse.OptionParser(
        usage='%prog [options]',
        description='Target Generator',
        epilog='\nTarget file generator for OpenADMS.\n'
               'Licenced under the European Union Public Licence (EUPL) v.1.1.'
               '\nFor further information visit http://www.dabamos.de/.\n')

    parser.add_option('-t', '--targets',
                      dest='t_file',
                      action='store',
                      type='string',
                      help='path to the targets file',
                      default='targets.csv')

    parser.add_option('-c', '--commands',
                      dest='c_file',
                      action='store',
                      type='string',
                      help='path to the commands file',
                      default='commands.json')

    parser.add_option('-o', '--output',
                      dest='o_file',
                      action='store',
                      type='string',
                      help='path to the output file',
                      default='output.json')

    (options, args) = parser.parse_args()

    level = logging.DEBUG

    logger = logging.getLogger('targets')
    logger.setLevel(level)

    fmt = '%(asctime)s - %(levelname)7s - %(name)s - %(message)s'
    date_fmt = '%Y-%m-%dT%H:%M:%S'

    formatter = logging.Formatter(fmt)
    # Logging console handler.
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(level)
    ch.setFormatter(formatter)

    coloredlogs.install(level=level,
                        fmt=fmt,
                        datefmt=date_fmt)

    main(options.t_file, options.c_file, options.o_file)
