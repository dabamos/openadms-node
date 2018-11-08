#!/usr/bin/env python3

"""Target generator for OpenADMS. FOR TESTING ONLY. Reads a CSV file with
targets and a JSON file with observations/commands to merge them into a valid
sensor configuration. This tool will be deprecated in near future, once the user
interface has been finished."""

__author__ = 'Philipp Engel'
__copyright__ = 'Copyright (c) 2017 Hochschule Neubrandenburg'
__license__ = 'BSD-2-Clause'

import copy
import json
import logging.handlers
import math
import optparse
import os
import sys


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

    result = { 'observations': [] }

    for target in targets:
        t_name, t_hz, t_v = target.strip('\n').split(',')
        logger.debug('Target: {:>5}, Hz [gon]: {:>10}, V [gon]: {:>10}'
                     .format(t_name, t_hz, t_v))
        hz_rad = str(round(grad2rad(float(t_hz)), 5))
        v_rad = str(round(grad2rad(float(t_v)), 5))

        logger.debug('Target: {:>5}, Hz [rad]: {:>10}, V [rad]: {:>10}'
                     .format(t_name, hz_rad, v_rad))

        for command in commands:
            result['observations'].append(copy.deepcopy(command))
            l = len(result.get('observations'))
            obs_data = result.get('observations')[l - 1]

            if obs_data.get('target') is not None:
                obs_data['target'] = obs_data.get('target')\
                                             .replace('{{target}}', t_name)

            if obs_data.get('description') is not None:
                obs_data['description'] = obs_data.get('description')\
                                          .replace('{{target}}', t_name)

            if obs_data.get('name') is not None:
                obs_data['name'] = obs_data.get('name')\
                                           .replace('{{target}}', t_name)

            request_sets = obs_data['requestSets']

            for set_name, request_set in request_sets.items():
                request_set['request'] = request_set.get('request')\
                                         .replace('{{hz}}', hz_rad)
                request_set['request'] = request_set.get('request')\
                                         .replace('{{v}}', v_rad)

    output = json.dumps(result,
                        sort_keys=True,
                        indent=4,
                        separators=(',', ': '))

    with open(o_file, 'w') as f:
        f.write(output)
        logger.debug('Saved processed commands to {}'.format(o_file))

if __name__ == '__main__':
    optparse.OptionParser.format_epilog = lambda self, formatter: self.epilog
    parser = optparse.OptionParser(
        usage='%prog [options]',
        description='Target Generator',
        epilog='\nTarget file generator for OpenADMS.\n'
               'Licenced under BSD-2-Clause,'
               '\nFor further information visit https://www.dabamos.de/.\n')

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
    ch = logging.StreamHandler()
    ch.setLevel(level)
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    main(options.t_file, options.c_file, options.o_file)
