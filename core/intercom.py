#!/usr/bin/env python3
"""
Copyright (c) 2017 Hochschule Neubrandenburg.

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

import asyncio
import json
import logging

from threading import Thread
from typing import *

import paho.mqtt.client as mqtt

try:
    from hbmqtt.broker import Broker
except ImportError:
    logging.getLogger().error('Importing Python module "HBMQTT" failed')


class MQTTMessageBroker(Thread):
    """
    Wrapper class for the HBMQTT message broker.
    """

    def __init__(self, host: str, port: int):
        """
        Args:
            host: The host name (IP or FQDN).
            port: The port number.
        """
        super().__init__()
        self.daemon = True
        self.logger = logging.getLogger('mqtt')

        self._config = {
            'listeners': {
                'default': {
                    'max-connections': 5000,        # Set '0' for no limit.
                    'type': 'tcp',                  # Set 'ws' for WebSockets.
                    'bind': '{}:{}'.format(host,
                                           port)
                }
            }
        }

    def run(self) -> None:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        broker = Broker(config=self._config)

        try:
            loop.run_until_complete(broker.start())
            self.logger.info('Starting MQTT message broker')
            loop.run_forever()
        except KeyboardInterrupt:
            loop.run_until_complete(broker.shutdown())
        finally:
            loop.close()


class MQTTMessenger(object):
    """
    MQTTMessenger connects to an MQTT message broker and exchanges messages.
    """

    def __init__(self, manager: Any, client_id: str):
        """
        Args:
            manager: The manager object.
            client_id: The MQTT client id.
        """
        self.logger = logging.getLogger('mqtt')

        self._config_manager = manager.config_manager
        self._schema_manager = manager.schema_manager

        self._type = 'core.intercom.MQTTMessenger'
        config = self.get_config('intercom', 'mqtt')

        self._client = None
        self._client_id = client_id
        self._host = config.get('host')
        self._port = config.get('port')
        self._keep_alive = config.get('keepAlive')
        self._topic = config.get('topic')

        # Function to send received messages to.
        self._downlink = None

        # MQTT client configuration.
        self._client = mqtt.Client(self._client_id)
        self._client.on_connect = self._on_connect
        self._client.on_disconnect = self._on_disconnect
        self._client.on_message = self._on_message

    def __del__(self):
        if self._client:
            self.disconnect()

    def _on_connect(self,
                    client: Type[mqtt.Client],
                    userdata: Any,
                    flags: Dict[str, int],
                    rc: int) -> None:
        """Callback method is called after a connection has been
        established."""
        self._client.subscribe(self._topic)

    def _on_disconnect(self,
                       client: Type[mqtt.Client],
                       userdata: Any,
                       rc: int) -> None:
        """Callback method is called after disconnection."""
        if rc != 0:
            self.logger.error('Unexpected disconnection from {}:{}'
                              .format(self._host, self._port))
            self.logger.info('Reconnecting to {}:{} ...'
                             .format(self._host, self._port))
            self.connect()

    def _on_message(self,
                    client: Type[mqtt.Client],
                    userdata: Any,
                    msg: Type[mqtt.MQTTMessage]) -> None:
        """Callback method for incoming messages. Converts the JSON-based
        message to its real data type and then forwards it to the downlink
        function."""
        try:
            data = json.loads(str(msg.payload, encoding='UTF-8'))
            self._downlink(data)
        except json.JSONDecodeError:
            self.logger.error('Message from client "{}" is corrupted '
                              '(invalid JSON)'.format(client))

    def connect(self) -> None:
        """Connect to the message broker."""
        if self._client:
            self._client.connect_async(self._host,
                                       self._port,
                                       self._keep_alive)
            self._client.loop_start()
        else:
            self.logger.error('Can\'t create connection to MQTT message broker')

    def disconnect(self) -> None:
        """Disconnect from the message broker."""
        if self._client:
            self._client.loop_stop()
            self._client.disconnect()

    def get_config(self, *args: List[str]) -> Dict[str, Any]:
        """Returns the validated configuration of the module.

        Args:
            *args: Key names to the configuration in the dictionary.

        Returns:
            A dictionary with the module's configuration.
        """
        schema_path = self._schema_manager.get_schema_path(self._type)

        return self._config_manager.get_valid_config(self._type,
                                                     schema_path,
                                                     *args)

    def publish(self, topic: str, message: str) -> None:
        """Send message to the message broker."""
        self._client.publish(topic, message)

    def subscribe(self, topic) -> None:
        """Set the topic the client should subscribe from the message
        broker."""
        self._topic = topic

    @property
    def client(self) -> mqtt.Client:
        return self._client

    @property
    def downlink(self) -> Callable[[List[Dict]], None]:
        return self._downlink

    @property
    def host(self) -> str:
        return self._host

    @property
    def port(self) -> int:
        return self._port

    @property
    def topic(self) -> str:
        return self._topic

    @downlink.setter
    def downlink(self, downlink: Callable[[List[Dict]], None]):
        """Register a callback function which is called after a message has
        been received.

        Args:
            downlink: The downlink function.
        """
        self._downlink = downlink
