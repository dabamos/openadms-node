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

import json
import logging
import paho.mqtt.client as mqtt

logger = logging.getLogger('openadms')


class MQTTMessenger(object):

    """
    MQTTMessenger connects to an MQTT message broker and exchanges messages.
    """

    def __init__(self, config_manager):
        self._config_manager = config_manager
        config = self._config_manager.get('Intercom').get('MQTT')

        self._client_id = None
        self._host = config.get('Host')
        self._port = config.get('Port')
        self._keepalive = config.get('KeepAlive')
        self._topic = config.get('Topic')

        self._uplink = None

        self._client = mqtt.Client(self._client_id)
        self._client.on_connect = self._on_connect
        self._client.on_disconnect = self._on_disconnect
        self._client.on_message = self._on_message

    def __del__(self):
        self.disconnect()

    def connect(self):
        """Connect to the message broker."""
        self._client.connect_async(self._host, self._port, self._keepalive)
        self._client.loop_start()

    def disconnect(self):
        """Disconnect from the message broker."""
        if self._client:
            self._client.loop_stop()
            self._client.disconnect()

    def _on_connect(self, client, userdata, flags, rc):
        """Callback method is called after a connection has been
        established."""
        logger.debug('Connected to {}:{}'.format(self._host, self._port))
        self._client.subscribe(self._topic)

    def _on_disconnect(self, client, userdata, rc):
        """Callback method is called after disconnection."""
        if rc != 0:
            logger.error('Unexpected disconnection from {}:{}'
                         .format(self._host, self._port))

    def _on_message(self, client, userdata, msg):
        """Callback method for incoming messages."""
        data = json.loads(str(msg.payload, encoding='UTF-8'))
        self._uplink(data)

    def publish(self, topic, message):
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
    def topic(self):
        return self._topic

    @property
    def uplink(self):
        return self._uplink

    @uplink.setter
    def uplink(self, uplink):
        """Register a callback function which is called after a message has
        been received."""
        self._uplink = uplink
