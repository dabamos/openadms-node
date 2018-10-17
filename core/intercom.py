#!/usr/bin/env python3.6

import asyncio
import json
import logging

from threading import Thread
from typing import Any, Callable, Dict, List, Type

import paho.mqtt.client as paho

try:
    from hbmqtt.broker import Broker
except ImportError:
    logging.getLogger().critical('Importing Python module "HBMQTT" failed')


class MQTTMessageBroker(Thread):
    """
    Wrapper class for the HBMQTT message broker.
    """

    def __init__(self, host: str = '127.0.0.1', port: int = 1883):
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
                    'max-connections': 50000,
                    'bind': f'{host}:{port}',
                    'type': 'tcp',
                },
            },
            'auth': {
                'allow-anonymous': True
            },
            'plugins': ['auth_anonymous'],
            'topic-check': {
                'enabled': False
            },
        }

    def run(self) -> None:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        broker = Broker(config=self._config)

        try:
            loop.run_until_complete(broker.start())
            self.logger.info('Starting local MQTT message broker ...')
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

        self._type = 'core.intercom.MQTTMessenger'
        self._client = None

        self._config_manager = manager.config_manager
        self._schema_manager = manager.schema_manager

        config = self._get_config('intercom', 'mqtt')

        self._client_id = client_id
        self._host = config.get('host')
        self._port = config.get('port')
        self._keep_alive = config.get('keepAlive')
        self._topic = config.get('topic')
        self._user = config.get('user') or ''
        self._password = config.get('password') or ''

        # Function to send received messages to.
        self._downlink = None

        # MQTT client configuration.
        self._client = paho.Client(client_id=self._client_id,
                                   clean_session=True,
                                   userdata=None,
                                   protocol=paho.MQTTv311)

        if len(self._user) > 0 and len(self._password) > 0:
            self._client.username_pw_set(self._user, self._password)

        self._client.on_connect = self._on_connect
        self._client.on_disconnect = self._on_disconnect
        self._client.on_message = self._on_message

    def __del__(self):
        if self._client:
            self.disconnect()

    def _get_config(self, *args):
        """Returns the validated configuration of the module. If no JSON schemas
        is available, the function just returns an unchecked configuration.

        Args:
            *args: Key names to the configuration in the dictionary.

        Returns:
            A dictionary with the module's configuration.
        """
        # Add the JSON schemas to the Schema Manager.
        schema_path = self._schema_manager.get_schema_path(self._type)
        self._schema_manager.add_schema(self._type, schema_path)

        # Return a valid configuration for the module or raise an exception.
        return self._config_manager.get_valid_config(self._type, 'core', *args)

    def _on_connect(self,
                    client: Type[paho.Client],
                    userdata: Any,
                    flags: Dict[str, int],
                    rc: int) -> None:
        """Callback method is called after a connection has been
        established."""
        self._client.subscribe(self._topic)

    def _on_disconnect(self,
                       client: Type[paho.Client],
                       userdata: Any,
                       rc: int) -> None:
        """Callback method is called after disconnection."""
        if rc != 0:
            self.logger.error(f'Unexpected disconnection from '
                              f'{self._host}:{self._port}')
            self.logger.info(f'Reconnecting to {self._host}:{self._port} ...')
            self.connect()

    def _on_message(self,
                    client: Type[paho.Client],
                    userdata: Any,
                    msg: Type[paho.MQTTMessage]) -> None:
        """Callback method for incoming messages. Converts the JSON-based
        message to its real data type and then forwards it to the downlink
        function."""
        try:
            data = json.loads(str(msg.payload, encoding='UTF-8'))
            self._downlink(data)
        except json.JSONDecodeError:
            self.logger.error(f'Message from client "{client}" is corrupted '
                              f'(invalid JSON)')

    def connect(self) -> None:
        """Connect to the message broker."""
        if self._client:
            self._client.connect_async(host=self._host,
                                       port=self._port,
                                       keepalive=self._keep_alive,
                                       bind_address='')
            self._client.loop_start()
        else:
            self.logger.error('Can\'t connect to MQTT message broker')

    def disconnect(self) -> None:
        """Disconnect from the message broker."""
        if self._client:
            self._client.loop_stop()
            self._client.disconnect()

    def publish(self, topic: str, message: str) -> None:
        """Send message to the message broker."""
        self._client.publish(topic, message)

    def subscribe(self, topic) -> None:
        """Set the topic the client should subscribe from the message
        broker."""
        self._topic = topic

    @property
    def client(self) -> paho.Client:
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
