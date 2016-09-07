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

import logging
import paho.mqtt.client as mqtt

logger = logging.getLogger('openadms')


class MQTTMessenger(object):

    """
    MQTTMessenger connects to an MQTT message broker and exchanges messages.
    """

    def __init__(self, host, port=1883, keepalive=60):
        self._host = host
        self._port = port
        self._keepalive = keepalive
        self._topic = '#'

        self._callback_func = None

        self._client = mqtt.Client()
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
        self._client.loop_stop()
        self._client.disconnect()

    def _on_connect(self, client, userdata, flags, rc):
        """Callback method is called after a connection has been
        established."""
        self._client.subscribe(self._topic)

    def _on_disconnect(self, client, userdata, rc):
        """Callback method is called after disconnection."""
        if rc != 0:
            logger.error('Unexpected disconnection')

    def _on_message(self, client, userdata, msg):
        """Callback method for incoming messages."""
        self._callback_func(str(msg.payload, encoding='UTF-8'))

    def publish(self, topic, message):
        """Send message to the message broker."""
        self._client.publish(topic, message)

    def register(self, callback_func):
        """Register a callback function which is called after a message has
        been received."""
        self._callback_func = callback_func

    def subscribe(self, topic):
        """Set the topic the client should subscribe from the message
        broker."""
        self._topic = topic

    @property
    def client(self):
        return self._client
