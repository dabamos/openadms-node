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

"""OpenADMS with Graphical Launcher

This Python script starts OpenADMS by using a graphical launcher. You have to
install the Python modules `wxPython` and `Gooey` with pip at first:

    $ python -m pip install gooey

For more information, please see https://www.dabamos.de/.
"""

__author__ = 'Philipp Engel'
__copyright__ = 'Copyright (c) 2017 Hochschule Neubrandenburg'
__license__ = 'EUPL'

from gooey import Gooey, GooeyParser

from openadms import *

logger = logging.getLogger()


@Gooey(advanced=True,
       language='english',
       program_name=('OpenADMS {} '
                     '- Open Automatic Deformation Monitoring System'
                     .format(System.get_openadms_version())),
       default_size=(610, 580),
       monospace_display=True,
       image_dir='./res')
def mainw() -> None:
    parser = GooeyParser(
        description='OpenADMS {} - Open Automatic Deformation Monitoring '
                    'System'.format(System.get_openadms_version()))

    parser.add_argument('-c', '--config',
                        metavar='Configuration File',
                        help='Path to the configuration file',
                        dest='config_file_path',
                        action='store',
                        default='./config/config.json',
                        required=True,
                        widget='FileChooser')
    parser.add_argument('-v', '--verbosity',
                        metavar='Verbosity Level (1 - 5)',
                        help='Log more diagnostic messages',
                        dest='verbosity',
                        action='count',
                        default=3)
    parser.add_argument('-d', '--debug',
                        metavar='Debug',
                        help='Print debug messages',
                        dest='is_debug',
                        action='store_true',
                        default=False)
    parser.add_argument('-m', '--with-mqtt-broker',
                        metavar='MQTT',
                        help='Run internal MQTT message broker',
                        dest='is_mqtt_broker',
                        action='store_true',
                        default=True)
    parser.add_argument('-l', '--log-file',
                        metavar='Log File',
                        help='Path to log file',
                        dest='log_file',
                        action='store',
                        default='openadms.log',
                        widget='FileChooser')
    parser.add_argument('-b', '--bind',
                        metavar='Host',
                        help='IP address or FQDN of internal broker',
                        dest='host',
                        action='store',
                        default='127.0.0.1')
    parser.add_argument('-p', '--port',
                        metavar='Port',
                        help='Port of internal broker',
                        dest='port',
                        action='store',
                        type=int,
                        default=1883)
    args = parser.parse_args()

    try:
        valid_path(args.config_file_path)
    except argparse.ArgumentTypeError as e:
        logger.error(e)
        return

    setup_logging(args.is_debug, args.verbosity, args.log_file)

    if args.is_mqtt_broker:
        # Use internal MQTT message broker (HBMQTT).
        start_mqtt_message_broker(args.host, args.port)

    main(args.config_file_path)


if __name__ == '__main__':
    setup_thread_exception_hook()
    sys.excepthook = exception_hook
    signal.signal(signal.SIGINT, signal_handler)
    mainw()
