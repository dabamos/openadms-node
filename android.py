#!/usr/bin/env python3.7

import argparse
import logging.handlers
import signal
import sys
import time
import traceback
import types

from pathlib import Path
from threading import Thread
from typing import Any

from core.system import System
from openadms import (exception_hook, get_args, main, setup_logging,
                      setup_thread_exception_hook, sighup_handler,
                      sigint_handler, start_mqtt_message_broker)

CONFIG_FILE_PATH = './config/examples/virtual.json'


if __name__ == '__main__':
    # Add OpenADMS directory to the Python system path.
    sys.path.append(System.get_root_dir())

    # Set the hook for unhandled exceptions.
    setup_thread_exception_hook()
    sys.excepthook = exception_hook

    # Use signal handlers to quit gracefully on SIGINT and to restart on SIGHUP.
    signal.signal(signal.SIGINT, sigint_handler)
    signal.signal(signal.SIGHUP, sighup_handler)

    # Get command-line arguments.
    args = get_args()
    args.config_file_path = CONFIG_FILE_PATH
    args.is_debug         = True

    # Initialise the logger.
    setup_logging(args.is_quiet, args.is_debug, args.verbosity, args.log_file)

    # Use internal MQTT message broker (HBMQTT).
    start_mqtt_message_broker(args.host, args.port)

    # Start the monitoring.
    main(args.config_file_path)

