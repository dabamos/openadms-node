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

import logging.handlers
import optparse
import signal
import sys
import time

import coloredlogs

from core.monitor import Monitor

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

# Get root logger.
logger = logging.getLogger()

LOG_FILE = 'openadms.log'
LOG_FILE_BACKUP_COUNT = 1
MAX_LOG_FILE_SIZE = 10485760    # 10 MB.

VERSION = 0.4
VERSION_NAME = 'Dar es Salaam'


def main(config_file):
    # v = 'v.{} ({})'.format(VERSION, VERSION_NAME)
    v = 'v.{}'.format(VERSION)

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

    # Start the monitoring.
    Monitor(config_file)
    # Run to infinity and beyond (probably not).
    stay_alive()

def signal_handler(signal, frame):
    logger.info('Exiting ...')
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
               '\nFor further information, visit http://www.dabamos.de/.\n')

    parser.add_option('-c', '--config',
                      dest='config_file',
                      action='store',
                      type='string',
                      help='path to the configuration file',
                      default='config/config.json')

    parser.add_option('-v', '--verbosity',
                      dest='verbosity',
                      action='store',
                      type='int',
                      help='log more diagnostic messages',
                      default=3)

    parser.add_option('-d', '--debug',
                      dest='debug',
                      action='store_true',
                      help='print debug messages',
                      default=False)

    (options, args) = parser.parse_args()

    # Basic logging configuration.
    console_level = logging.DEBUG if options.debug else logging.INFO
    logger.setLevel(console_level)

    fmt = '%(asctime)s - %(levelname)7s - %(name)26s - %(message)s'
    formatter = logging.Formatter(fmt)

    # File handler.
    file_level = {
        1: logging.CRITICAL,
        2: logging.ERROR,
        3: logging.WARNING,
        4: logging.INFO,
        5: logging.DEBUG
    }.get(options.verbosity, 3)

    fh = logging.handlers.RotatingFileHandler(LOG_FILE,
                                              maxBytes=MAX_LOG_FILE_SIZE,
                                              backupCount=LOG_FILE_BACKUP_COUNT,
                                              encoding='utf8')
    fh.setLevel(file_level)
    fh.setFormatter(formatter)

    # Add handler to logger.
    logger.addHandler(fh)

    date_fmt = '%Y-%m-%dT%H:%M:%S'
    coloredlogs.install(level=console_level, fmt=fmt, datefmt=date_fmt)

    # Use a signal handler to catch ^C and quit the program gracefully.
    signal.signal(signal.SIGINT, signal_handler)
    # Start the main program.
    main(options.config_file)
