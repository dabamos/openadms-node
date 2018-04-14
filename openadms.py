#!/usr/bin/env python3.6

"""OpenADMS - Open Automatic Deformation Monitoring System

The Open Automatic Deformation Monitoring System (OpenADMS) is a free and
open-source software for permanent observations. It can be used to monitor
buildings, terrain, and other objects with the help of geodetical or
geotechnical sensors.

The OpenADMS Node software runs on single sensor node instances in a sensor
network to obtain the measured data of total stations, digital levels,
inclinometers, weather stations, GNSS receivers, and other sensors. The raw
data is then processed, analysed, stored, and transmitted.

Example:
    You can either use the internal MQTT message broker or an external one,
    like Eclipse Mosquitto. The external broker has to be started before
    OpenADMS Node.

    To start OpenADMS Node with the internal broker, run::

        $ python3 openadms.py -c config/my_config.json -m -d

    The monitoring will begin automatically.
"""

__author__ = 'Philipp Engel'
__copyright__ = 'Copyright (c) 2017 Hochschule Neubrandenburg'
__license__ = 'BSD-2-Clause'

import argparse
import logging.handlers
import signal
import sys
import time
import traceback
import types

from pathlib import Path
from threading import Thread
from typing import *

import coloredlogs
import verboselogs

from core.intercom import MQTTMessageBroker
from core.logging import RootFilter
from core.monitor import Monitor
from core.system import System

# Get root logger.
root = logging.getLogger()

# Global Monitor.
monitor = None

LOG_FILE_BACKUP_COUNT = 1     # 1 log file only.
LOG_FILE_MAX_SIZE = 10485760  # 10 MiB.


def main(config_file_path: str) -> None:
    """Main procedure.

    Args:
        config_file_path: The path to the configuration file.
    """
    global monitor
    v = 'v.{}'.format(System.get_openadms_version())

    logger = logging.getLogger('openadms')
    logger.info('-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-')
    logger.info(' _____             _____ ____  _____ _____')
    logger.info('|     |___ ___ ___|  _  |    \|     |   __|')
    logger.info('|  |  | . | -_|   |     |  |  | | | |__   |')
    logger.info('|_____|  _|___|_|_|__|__|____/|_|_|_|_____|')
    logger.info('      |_|                        Node {}'.format(v))
    logger.info('')
    logger.info('Copyright (c) Hochschule Neubrandenburg')
    logger.info('Licenced under BSD-2-Clause')
    logger.info('-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-')

    # Start the monitoring.
    monitor = Monitor(config_file_path)
    monitor.start()

    # Run to infinity and beyond (probably not).
    stay_alive()


def setup_thread_exception_hook() -> None:
    """Workaround for `sys.excepthook` thread bug from:
    https://bugs.python.org/issue1230540

    Call once from the main thread before creating any threads."""
    init_original = Thread.__init__

    def init(self, *args, **kwargs):
        init_original(self, *args, **kwargs)
        run_original = self.run

        def run_with_exception_hook(*args2, **kwargs2):
            try:
                run_original(*args2, **kwargs2)
            except Exception:
                sys.excepthook(*sys.exc_info())

        self.run = run_with_exception_hook

    Thread.__init__ = init


def exception_hook(type: BaseException,
                   value: Exception,
                   tb: types.TracebackType) -> None:
    """Sets a hook for logging unhandled exceptions."""
    fmt_exception = ''.join(traceback.format_exception(type,
                                                       value,
                                                       tb)).replace('\n', '')
    root.critical('Unhandled exception: {}'
                  .format(' '.join(fmt_exception.split())))


def sighup_handler(signalnum: int, frame: Any) -> None:
    global monitor
    root.info('Caught SIGHUP')

    if monitor:
        monitor.restart()

def sigint_handler(signalnum: int, frame: Any) -> None:
    """Outputs a message before quitting the application."""
    global monitor
    root.info('Caught SIGINT')

    if monitor:
        monitor.kill()
        time.sleep(3.0)

    root.info('Exiting ...')
    sys.exit(0)


def stay_alive() -> None:
    """Runs a loop infinitely."""
    while True:
        time.sleep(1)


def valid_path(string: str) -> str:
    """Checks whether a given string is a valid file path. Used as a validator
    for ``argparse.ArgumentParser``.

    Args:
        string: The string.

    Returns:
        The string with the valid path.

    Raises:
        argparse.ArgumentTypeError: If string is not a valid file path.
    """
    path = Path(string)

    if not path.exists() or not path.is_file():
        msg = '"{}" is not a valid configuration file'.format(string)
        raise argparse.ArgumentTypeError(msg)

    return string


def setup_logging(is_quiet: bool = False,
                  is_debug: bool = False,
                  verbosity: int = 6,
                  log_file: str = 'openadms.log') -> None:
    """Setups the logger and logging handlers.

    Args:
        is_quiet: Disable output.
        is_debug: Print debug messages.
        verbosity: Verbosity level (1 - 9).
        log_file: Path of the log file.
    """
    # Enable verbose logging.
    verboselogs.install()

    # Basic logging configuration.
    console_level = logging.DEBUG if is_debug else logging.INFO
    root.setLevel(console_level)

    fmt = '%(asctime)s - %(levelname)8s - %(name)26s - %(message)s'
    date_fmt = '%Y-%m-%dT%H:%M:%S'
    formatter = logging.Formatter(fmt, date_fmt)

    # File handler.
    file_level = {
        1: logging.CRITICAL,
        2: logging.ERROR,
        3: verboselogs.SUCCESS,
        4: logging.WARNING,
        5: verboselogs.NOTICE,
        6: logging.INFO,
        7: verboselogs.VERBOSE,
        8: logging.DEBUG,
        9: verboselogs.SPAM
    }.get(verbosity, 6)

    fh = logging.handlers.RotatingFileHandler(log_file,
                                              maxBytes=LOG_FILE_MAX_SIZE,
                                              backupCount=LOG_FILE_BACKUP_COUNT,
                                              encoding='utf8')
    fh.setLevel(file_level)
    fh.setFormatter(formatter)
    root.addHandler(fh)

    if is_quiet:
        # Silence logger output.
        console_level = 100

    # Colourised output of log messages.
    coloredlogs.install(level=console_level,
                        fmt=fmt,
                        datefmt=date_fmt,
                        logger=root)

    # Add filter to log handlers, to exclude log messages from HBMQTT.
    for handler in logging.root.handlers:
        handler.addFilter(RootFilter())


def start_mqtt_message_broker(host: str = '127.0.0.1',
                              port: int = 1883) -> None:
    """Starts the internal MQTT message broker.

    Args:
        host: FQDN or IP address.
        port: Port number.
    """
    broker = MQTTMessageBroker(host, port)
    broker.start()


if __name__ == '__main__':
    # Add OpenADMS directory to the Python system path.
    sys.path.append(System.get_root_dir())

    # Set the hook for unhandled exceptions.
    setup_thread_exception_hook()
    sys.excepthook = exception_hook

    # Use signal handlers to quit gracefully and restart on SIGUP.
    signal.signal(signal.SIGINT, sigint_handler)
    signal.signal(signal.SIGHUP, sighup_handler)

    # Parse command-line options.
    parser = argparse.ArgumentParser(
        usage='%(prog)s [options]',
        description='OpenADMS Node {} - Open Automatic Deformation Monitoring '
                    'System'.format(System.get_openadms_version()),
        epilog='OpenADMS Node has been developed at the Neubrandenburg '
               'University of Applied Sciences (Germany). Licenced under '
               'BSD-2-Clause. For further information, visit '
               'https://www.dabamos.de/.')

    # Optional arguments.
    parser.add_argument('-v', '--verbosity',
                        help='log more diagnostic messages',
                        dest='verbosity',
                        action='store',
                        type=int,
                        default=6,
                        choices=[1, 2, 3, 4, 5, 6, 7, 8, 9])
    parser.add_argument('-d', '--debug',
                        help='print debug messages',
                        dest='is_debug',
                        action='store_true',
                        default=False)
    parser.add_argument('-q', '--quiet',
                        help='do not output log messages',
                        dest='is_quiet',
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

    # Required arguments.
    required_args = parser.add_argument_group('required arguments')
    required_args.add_argument('-c', '--config',
                               help='path to configuration file',
                               dest='config_file_path',
                               action='store',
                               type=valid_path,
                               default='config/config.json',
                               required=True)

    try:
        # Parse arguments.
        args = parser.parse_args()
    except argparse.ArgumentTypeError as e:
        root.error(e)
        sys.exit(0)

    # Initialise the logger.
    setup_logging(args.is_quiet, args.is_debug, args.verbosity, args.log_file)

    if args.is_mqtt_broker:
        # Use internal MQTT message broker (HBMQTT).
        start_mqtt_message_broker(args.host, args.port)

    # Start the monitoring.
    main(args.config_file_path)
