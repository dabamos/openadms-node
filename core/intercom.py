#!/usr/bin/env python3
"""
Copyright (c) 2016 Hochschule Neubrandenburg.

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

import json
import logging

from typing import *

import paho.mqtt.client as mqtt


class MQTTMessenger(object):
    """
    MQTTMessenger connects to an MQTT message broker and exchanges messages.
    """

    def __init__(self, config_manager):
        self.logger = logging.getLogger('mqtt')
        self._config = config_manager.get('intercom').get('mqtt')

        self._client_id = None
        self._host = self._config.get('host')
        self._port = self._config.get('port')
        self._keep_alive = self._config.get('keepAlive')
        self._topic = self._config.get('topic')

        # Function to send received messages to.
        self._downlink = None

        # MQTT client configuration.
        self._client = mqtt.Client(self._client_id)
        self._client.on_connect = self._on_connect
        self._client.on_disconnect = self._on_disconnect
        self._client.on_message = self._on_message

    def __del__(self):
        self.disconnect()

    def _on_connect(self, client, userdata, flags, rc):
        """Callback method is called after a connection has been
        established."""
        #self.logger.debug('Connected to {}:{}'.format(self._host, self._port))
        self._client.subscribe(self._topic)

    def _on_disconnect(self, client, userdata, rc):
        """Callback method is called after disconnection."""
        if rc != 0:
            self.logger.error('Unexpected disconnection from {}:{}'
                              .format(self._host, self._port))
            self.logger.info('Reconnecting to {}:{} ...'
                             .format(self._host, self._port))
            self.connect()

    def _on_message(self, client, userdata, msg):
        """Callback method for incoming messages. Converts the JSON-based
        message to its real data type and then forwards it to the downlink
        function."""
        try:
            data = json.loads(str(msg.payload, encoding='UTF-8'))
            self._downlink(data)
        except json.JSONDecodeError:
            self.logger.error('Message from client "{}" is corrupted '
                              '(invalid JSON)'.format(client))

    def connect(self):
        """Connect to the message broker."""
        if self._client:
            self._client.connect_async(self._host,
                                       self._port,
                                       self._keep_alive)
            self._client.loop_start()
        else:
            self.logger.error('Can\'t create connection to MQTT message broker')

    def disconnect(self):
        """Disconnect from the message broker."""
        if self._client:
            self._client.loop_stop()
            self._client.disconnect()

    def publish(self, topic: str, message: str) -> None:
        """Send message to the message broker."""
        self._client.publish(topic, message)

    def subscribe(self, topic):
        """Set the topic the client should subscribe from the message
        broker."""
        self._topic = topic

    @property
    def client(self):
        return self._client

    @property
    def downlink(self):
        return self._downlink

    @property
    def host(self):
        return self._host

    @property
    def port(self):
        return self._port

    @property
    def topic(self):
        return self._topic

    @downlink.setter
    def downlink(self, downlink):
        """Register a callback function which is called after a message has
        been received."""
        self._downlink = downlink
