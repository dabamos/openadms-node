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
import logging
import logging.handlers
import optparse
import signal
import sys
import time

from core import monitor

"""OpenADMS - Open Automatic Deformation Monitoring System

OpenADMS is an open source automatic deformation monitoring system for
surveillance measurements. It can be used to monitor buildings, terrain, and
other objects with the help of geodetical or geotechnical sensors.

Example:
    At first, start an MQTT message broker like Eclipse Mosquitto. The message
    broker is used for distributing the messages of the OpenADMS modules. On
    Unix, Mosquitto can be started with:

        $ sudo service mosquitto onestart

    Then start OpenADMS with a valid configuration file:

        $ python3 openadms.py --config ./config/my_config.json

    The monitoring will begin automatically.
"""

logger = logging.getLogger('openadms')

LOG_FILE = 'openadms.log'
VERSION = 0.3
VERSION_NAME = 'Copenhagen'


def main(config_file):
    v = 'v.{} ({})'.format(VERSION, VERSION_NAME)

    logger.info('-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-')
    logger.info(' _____             _____ ____  _____ _____')
    logger.info('|     |___ ___ ___|  _  |    \|     |   __|')
    logger.info('|  |  | . | -_|   |     |  |  | | | |__   |')
    logger.info('|_____|  _|___|_|_|__|__|____/|_|_|_|_____|')
    logger.info('      |_| {:>33}'.format(v))
    logger.info('')
    logger.info('Copyright (c) Hochschule Neubrandenburg')
    logger.info('European Union Public Licence (EUPL) v.1.1')
    logger.info('-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-')

    # Start the monitor.
    mon = monitor.Monitor(config_file)
    # Run to infinity and beyond (probably not).
    stay_alive()

def signal_handler(signal, frame):
    logger.info('Quitting ...')
    sys.exit(0)

def stay_alive():
    while True:
        time.sleep(1)

if __name__ == '__main__':
    optparse.OptionParser.format_epilog = lambda self, formatter: self.epilog
    parser = optparse.OptionParser(
        usage='%prog [options]',
        description='OpenADMS {}'.format(VERSION),
        epilog='\nOpenADMS has been developed at the University of Applied '
               'Sciences Neubrandenburg (Germany).\n'
               'Licenced under the European Union Public Licence (EUPL) v.1.1.'
               '\nFor further information visit http://www.dabamos.de/.\n')

    parser.add_option('-c', '--config',
                      dest='config_file',
                      action='store',
                      type='string',
                      help='path to the configuration file',
                      default='config/config.json')

    parser.add_option('-v', '--verbose',
                      dest='verbosity',
                      action='store',
                      type='int',
                      help='print more diagnostic messages',
                      default=5)

    (options, args) = parser.parse_args()

    level = {
        1: logging.CRITICAL,
        2: logging.ERROR,
        3: logging.WARNING,
        4: logging.INFO,
        5: logging.DEBUG
    }.get(options.verbosity, logging.DEBUG)

    # Basic logging configuration.
    logger.setLevel(level)

    # '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    fmt = '%(asctime)s - %(levelname)7s - %(module)12s - %(message)s'
    date_fmt = '%Y-%m-%dT%H:%M:%S'

    formatter = logging.Formatter(fmt)
    # Logging file handler.
    fh = logging.handlers.RotatingFileHandler(LOG_FILE,
                                              maxBytes=10485760,  # 10 MB
                                              backupCount=1,
                                              encoding='utf8')
    fh.setLevel(level)
    fh.setFormatter(formatter)

    # Add handlers to logger.
    logger.addHandler(fh)

    coloredlogs.install(level=level,
                        fmt=fmt,
                        datefmt=date_fmt)

    # Use a signal handler to catch ^C and quit the program gracefully.
    signal.signal(signal.SIGINT, signal_handler)

    # Start the main program.
    main(options.config_file)
