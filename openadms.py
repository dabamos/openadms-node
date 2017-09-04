#!/usr/bin/env python3
"""
Copyright (c) 2017 Hochschule Neubrandenburg an other contributors.

Licenced under the EUPL, Version 1.1 or - as soon they will be approved
by the European Commission - subsequent versions of the EUPL (the
"Licence");

You may not use this work except in compliance with the Licence.

You may obtain a copy of the Licence at:

    https://joinup.ec.europa.eu/community/eupl/og_page/eupl

Unless required by applicable law or agreed to in writing, software
distributed under the Licence is distributed on an "AS IS" basis,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the Licence for the specific language governing permissions and
limitations under the Licence.
"""

"""OpenADMS - Open Automatic Deformation Monitoring System

OpenADMS is an open source automatic deformation monitoring system for permanent
observations. It can be used to monitor buildings, terrain, and other objects
with the help of geodetical or geotechnical sensors.

Example:
    You can either use the internal MQTT message broker or an external one,
    like Eclipse Mosquitto. The external broker has to be started before
    OpenADMS.

    Run OpenADMS with the internal broker:

        $ python3 openadms.py -c ./config/my_config.json -m -d

    The monitoring will begin automatically.
"""

__author__ = 'Philipp Engel'
__copyright__ = 'Copyright (c) 2017 Hochschule Neubrandenburg'
__license__ = 'EUPL'

import argparse
import coloredlogs
import logging.handlers
import optparse
import signal
import sys
import threading
import time
import traceback

from pathlib import Path

from core.intercom import MQTTMessageBroker
from core.logging import RootFilter
from core.monitor import Monitor
from core.system import System


# Get root logger.
logger = logging.getLogger()

LOG_FILE_BACKUP_COUNT = 1
MAX_LOG_FILE_SIZE = 10485760  # 10 MB.


def main(config_file: str) -> None:
    v = 'v.{}'.format(System.get_openadms_version())

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


def setup_thread_exception_hook() -> None:
    """Workaround for `sys.excepthook` thread bug from:
    https://bugs.python.org/issue1230540

    Call once from the main thread before creating any threads."""
    init_original = threading.Thread.__init__

    def init(self, *args, **kwargs):
        init_original(self, *args, **kwargs)
        run_original = self.run

        def run_with_exception_hook(*args2, **kwargs2):
            try:
                run_original(*args2, **kwargs2)
            except Exception:
                sys.excepthook(*sys.exc_info())

        self.run = run_with_exception_hook

    threading.Thread.__init__ = init


def exception_hook(type, value, tb) -> None:
    fmt_exception = ''.join(traceback.format_exception(type,
                                                       value,
                                                       tb)).replace('\n', '')
    logger.critical('Unhandled exception: {}'
                    .format(' '.join(fmt_exception.split())))


def signal_handler(signal, frame) -> None:
    logger.info('Exiting ...')
    sys.exit(0)


def stay_alive() -> None:
    while True:
        time.sleep(1)


def valid_path(string):
    path = Path(string)

    if not path.exists() or not path.is_file():
        msg = "{} is not a valid configuration file".format(string)
        raise argparse.ArgumentTypeError(msg)

    return string


if __name__ == '__main__':
    # Set the hook for unhandled exceptions.
    setup_thread_exception_hook()
    sys.excepthook = exception_hook

    # Use a signal handler to catch ^C and quit the program gracefully.
    signal.signal(signal.SIGINT, signal_handler)

    # Parse command line options.
    parser = argparse.ArgumentParser(
        usage='%prog [options]',
        description='OpenADMS {} - Open Automatic Deformation Monitoring '
                    'System'.format(System.get_openadms_version()),
        epilog='\nOpenADMS has been developed at the Neubrandenburg '
               'University of Applied Sciences (Germany).\n'
               'Licenced under the European Union Public Licence (EUPL) v.1.1.'
               '\nFor further information, visit https://www.dabamos.de/.\n')

    parser.add_argument('-c', '--config',
                        help='path to configuration file',
                        dest='config_file_path',
                        action='store',
                        type=valid_path,
                        default='config/config.json',
                        required=True)
    parser.add_argument('-v', '--verbosity',
                        help='log more diagnostic messages',
                        dest='verbosity',
                        action='store',
                        type=int,
                        default=3,
                        choices=[1, 2, 3, 4, 5])
    parser.add_argument('-d', '--debug',
                        help='print debug messages',
                        dest='is_debug',
                        action='store_true',
                        default=False)
    parser.add_argument('-l', '--log-file',
                        help='path to log file',
                        dest='log_file',
                        action='store',
                        default='openadms.log')
    parser.add_argument('-m', '--with-mqtt-broker',
                        help='use internal MQTT message broker',
                        dest='is_mqtt_broker',
                        action='store_true',
                        default=False)
    parser.add_argument('-b', '--bind',
                        help='host of MQTT message broker (IP address or FQDN)',
                        dest='host',
                        action='store',
                        default='127.0.0.1')
    parser.add_argument('-p', '--port',
                        help='port of MQTT message broker',
                        dest='port',
                        action='store',
                        type=int,
                        default=1883)

    args = parser.parse_args()

    # Basic logging configuration.
    console_level = logging.DEBUG if args.is_debug else logging.INFO
    logger.setLevel(console_level)

    fmt = '%(asctime)s - %(levelname)8s - %(name)26s - %(message)s'
    formatter = logging.Formatter(fmt)

    # File handler.
    file_level = {
        1: logging.CRITICAL,
        2: logging.ERROR,
        3: logging.WARNING,
        4: logging.INFO,
        5: logging.DEBUG
    }.get(args.verbosity, 3)

    fh = logging.handlers.RotatingFileHandler(args.log_file,
                                              maxBytes=MAX_LOG_FILE_SIZE,
                                              backupCount=LOG_FILE_BACKUP_COUNT,
                                              encoding='utf8')
    fh.setLevel(file_level)
    fh.setFormatter(formatter)
    logger.addHandler(fh)

    # Colorized output of log messages.
    date_fmt = '%Y-%m-%dT%H:%M:%S'
    coloredlogs.install(level=console_level, fmt=fmt, datefmt=date_fmt)

    # Use internal MQTT message broker (HBMQTT).
    if args.is_mqtt_broker:
        # Add filter to log handlers.
        for handler in logging.root.handlers:
            handler.addFilter(RootFilter())

        broker = MQTTMessageBroker(args.host, args.port)
        broker.start()

    # Start the monitoring.
    main(args.config_file_path)
