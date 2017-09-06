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

"""Module for alerting."""

__author__ = 'Philipp Engel'
__copyright__ = 'Copyright (c) 2017 Hochschule Neubrandenburg'
__license__ = 'EUPL'

import logging
import queue
import smtplib
import socket
import threading
import time

from datetime import datetime
from email.header import Header
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formatdate
from typing import *

from core.logging import RootFilter
from core.manager import Manager
from core.version import *
from module.prototype import Prototype


class Alert(Prototype):
    """
    Alert is used to send warning and error messages to other modules.
    """

    def __init__(self, module_name: str, module_type: str, manager: Manager):
        super().__init__(module_name, module_type, manager)
        config = self.get_config(self._name)

        self._is_enabled = config.get('enabled')
        self._thread = None
        self._queue = queue.Queue(1000)

        # Add logging handler to the root logger.
        qh = logging.handlers.QueueHandler(self._queue)
        qh.addFilter(RootFilter())
        qh.setLevel(logging.WARNING)    # Only get WARNING, ERROR, and CRITICAL.
        root = logging.getLogger()
        root.addHandler(qh)

        self._modules = config.get('modules')

    def fire(self, log):
        # Set the header.
        header = {'type': 'alert'}

        # Iterate through the message agent modules.
        for module_name, module in self._modules.items():
            if not module.get('enabled'):
                continue

            receivers = module.get('receivers').get(log.levelname.lower())

            if not receivers or len(receivers) == 0:
                self.logger.debug('No receivers defined for log level "{}"'
                                  .format(log.levelname.lower()))
                continue

            # Publish a single message for each receiver.
            for receiver in receivers:
                payload = {
                    'dt': log.asctime,
                    'level': log.levelname.lower(),
                    'message': log.message,
                    'receiver': receiver
                }

                self.publish(module_name, header, payload)

    def run(self):
        while self.is_running:
            log = self._queue.get()         # Blocking I/O.
            self.logger.info('Processing alert message')
            self.fire(log)

    def start(self):
        if self._is_running:
            return

        # self.logger.debug('Starting worker "{}"'
        #                   .format(self._name))
        self._is_running = True

        # Check the logging queue continuously for messages and proceed
        # them to the alert agents.
        self._thread = threading.Thread(target=self.run)
        self._thread.daemon = True
        self._thread.start()


class AlertMessageFormatter(Prototype):

    def __init__(self, module_name: str, module_type: str, manager: Manager):
        super().__init__(module_name, module_type, manager)
        self._config = self._config_manager.get(self._name)
        self._thread = None

        # Configuration.
        self._msg_collection_enabled =\
            self._config.get('messageCollectionEnabled')
        self._msg_collection_time = self._config.get('messageCollectionTime')
        self._receiver = self._config.get('receiver')
        self._templates = self._config.get('templates')

        # Message handler.
        self.add_handler('alert', self.handle_alert_message)

        # Queue for alert message collection.
        self._queue = queue.Queue(-1)

    def handle_alert_message(self,
                             header: Dict[str, Any],
                             payload: Dict[str, Any]) -> None:
        """Handles messages of type`alert` and either caches them or forwards
        them to the `process_alert_messages()` method.

        Args:
            header: The alert header.
            payload: The alert payload.
        """
        if self._msg_collection_enabled:
            # Add the alert message to the collection queue. It will be
            # processed by the threaded `run()` method later.
            self._queue.put(payload)
        else:
            # Process a single alert message.
            receiver = payload.get('receiver')
            self.process_alert_messages(receiver, [payload])

    def process_alert_messages(self,
                               receiver: str,
                               alerts: List[Dict[str, str]]) -> None:
        """
        Args:
            receiver: The receiver of the alert.
            alerts: The list of alert messages.
        """
        if not receiver or receiver == '':
            self.logger.warning('No receiver defined for alert message')
            return

        # Create the header of the message.
        header = {'type': self._config.get('type')}

        # Parse the properties.
        properties = {}

        for prop_name, prop in self._config.get('properties').items():
            properties[prop_name] = prop.replace('{{receiver}}', receiver)

        # Load the templates
        msg_header = self._templates.get('header')
        msg_footer = self._templates.get('footer')

        # Parse the header and the footer.
        msg_header = msg_header.replace('{{receiver}}', receiver)
        msg_footer = msg_footer.replace('{{receiver}}', receiver)

        # Append the alert messages line by line to the body of the template.
        msg_body = ''

        for key, value in alerts.items():
            # Add the line to the message body.
            line = self._templates.get('body')
            msg_body += line.replace('{{' + key + '}}', value)

        # Concatenate the message parts.
        complete_msg = ''.join([msg_header,
                                msg_body,
                                msg_footer])

        # Create the payload of the message.
        payload = properties
        payload['message'] = complete_msg

        # Fire and forget.
        self.publish(self._receiver, header, payload)

    def run(self) -> None:
        # Dictionary for caching alert messages. Stores a list of dictionaries:
        # '<receiver_name>': [<msg_1>, <msg_2>, ..., <msg_n>]
        cache = {}

        while self._is_running:
            try:
                # Get a message from the queue.
                msg = self._queue.get_nowait()

                # Check the receiver.
                receiver = msg.get('receiver')

                if not receiver:
                    self.logger.warning('No receiver defined in alert message')
                    continue

                # Create an empty list for the alert messages.
                if not cache.get(receiver):
                    cache[receiver] = []

                # Append the message to the list of the receiver.
                cache[receiver].append(msg)
            except queue.Empty:
                if len(cache) > 0:
                    for receiver, messages in cache.items():
                        if not messages or len(messages) == 0:
                            continue

                        self.process_alert_messages(receiver, messages)

                # Sleep some time.
                self.logger.debug('Waiting {} s to collect new alert messages'
                                  .format(self._msg_collection_time))
                time.sleep(self._msg_collection_time)

                # Clear the messages cache.
                cache.clear()

    def start(self) -> None:
        if self._is_running:
            return

        # self.logger.debug('Starting worker "{}"'
        #                   .format(self._name))
        self._is_running = True

        if self._msg_collection_enabled:
            # Threading for alert message collection.
            self._thread = threading.Thread(target=self.run)
            self._thread.daemon = True
            self._thread.start()


class MailAgent(Prototype):

    def __init__(self, module_name: str, module_type: str, manager: Manager):
        super().__init__(module_name, module_type, manager)
        config = self._config_manager.get(self._name)

        self._charset = config.get('charset')
        self._default_subject = config.get('defaultSubject',
                                           '[OpenADMS] Notification')
        self._default_from = 'OpenADMS'
        self._host = config.get('host')
        self._is_start_tls = config.get('startTls')
        self._is_tls = config.get('tls')
        self._port = config.get('port')
        self._user_mail = config.get('userMail')
        self._user_name = config.get('userName')
        self._user_password = config.get('userPassword')
        self._x_mailer = 'OpenADMS {} Mail Agent'.format(OPENADMS_VERSION)

        self.add_handler('email', self.handle_mail)

    def handle_mail(self,
                    header: Dict[str, Any],
                    payload: Dict[str, Any]) -> None:
        """Handles messages of type`email` and forwards them to the
        `process_mail()` method.

        Args:
            header: The message header.
            payload: The message payload.
        """
        mail_subject = payload.get('subject') or self._default_subject
        mail_from = payload.get('from') or self._user_mail
        mail_to = payload.get('to') or ''
        mail_message = payload.get('message') or ''

        self.process_mail(mail_from,
                          mail_to,
                          mail_subject,
                          mail_message)

    def process_mail(self,
                     mail_from: str,
                     mail_to: str,
                     mail_subject: str,
                     mail_message: str) -> None:
        """Sends emails by SMTP.

        Args:
            mail_from: The sender of the email.
            mail_to: The recipient of the email.
            mail_subject: The subject of the email.
            mail_message: The body test of the email.
        """
        if self._is_tls and self._is_start_tls:
            self.logger.critical('Invalid SSL configuration '
                                 '(select TLS or StartTLS)')
            return

        msg = MIMEMultipart('alternative')
        msg['From'] = '{} <{}>'.format(mail_from, self._user_mail)
        msg['To'] = mail_to
        msg['Date'] = formatdate(localtime=True)
        msg['X-Mailer'] = self._x_mailer
        msg['Subject'] = Header(mail_subject, self._charset)

        plain_text = MIMEText(mail_message.encode(self._charset),
                              'plain',
                              self._charset)

        msg.attach(plain_text)

        try:
            if self._is_tls:
                # Use TLS encryption.
                smtp = smtplib.SMTP_SSL(self._host, self._port)
            else:
                smtp = smtplib.SMTP(self._host, self._port)

            smtp.set_debuglevel(False)
            smtp.ehlo()

            if not self._is_tls and self._is_start_tls:
                # Use TLS via StartTLS.
                smtp.starttls()
                smtp.ehlo()

            smtp.login(self._user_name, self._user_password)
            smtp.sendmail(self._user_mail, [mail_to], msg.as_string())
            smtp.quit()

            self.logger.info('E-mail has been send successfully to {}'
                             .format(mail_to))
        except smtplib.SMTPException:
            self.logger.warning('E-mail could not be sent (SMTP error)')
        except TimeoutError:
            self.logger.warning('E-mail could not be sent (timeout)')


class ShortMessageAgent(Prototype):
    """
    ShortMessageAgent uses a socket connection to a GSM modem to send SMS.
    """

    def __init__(self, module_name: str, module_type: str, manager: Manager):
        super().__init__(module_name, module_type, manager)
        config = self._config_manager.get(self._name)

        self._host = config.get('host')
        self._port = config.get('port')

        # Capture messages of type 'sms'.
        self.add_handler('sms', self.handle_short_message)

    def handle_short_message(self,
                             header: Dict[str, Any],
                             payload: Dict[str, Any]) -> None:
        """Handles messages of type `sms`.

        Args:
            header: The message header.
            payload: The message payload.
        """
        number = payload.get('number')
        message = payload.get('message')

        if not number:
            self.logger.warning('No phone number defined in short message')
            return

        if not message:
            self.logger.warning('No message text defined in short message')
            return

        self.process_short_message(number, message)

    def process_short_message(self, number: str, message: str) -> None:
        """Sends an SMS to a socket server.

        Args:
            number: The number of the recipient (e.g., "+49 176 123456").
            message: The message text.
        """
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            try:
                sock.connect((self._host, self._port))
                self.logger.debug('Established connection to "{}:{}"'
                                  .format(self._host, self._port))
            except ConnectionRefusedError:
                self.logger.error('Could not connect to "{}:{}" '
                                  '(connection refused)'.format(self._host,
                                                                self._port))
                return
            except TimeoutError:
                self.logger.error('Could not connect to "{}:{}" (timeout)'
                                  .format(self._host, self._port))
                return

            self.logger.info('Sending SMS to "{}"'.format(number))
            sock.send(message.encode())

            self.logger.debug('Closed connection to "{}:{}"'
                     .format(self._host, self._port))


class Heartbeat(Prototype):
    """
    Heartbeat sends heartbeat messages ("pings") to the message broker.
    """

    def __init__(self, module_name: str, module_type: str, manager: Manager):
        super().__init__(module_name, module_type, manager)
        config = self._config_manager.get(self._name)

        self._receivers = config.get('receivers')
        self._interval = config.get('interval')

        self._thread = None
        self._header = {'type': 'heartbeat'}

        self.add_handler('heartbeat', self.process_heartbeat)

    def process_heartbeat(self,
                          header: Dict[str, Any],
                          payload: Dict[str, Any]) -> None:
        self.logger.info('Received heartbeat at "{}" UTC for project "{}"'
                         .format(payload.get('dt'),
                                 payload.get('projectId')))

    def run(self, sleep_time: float = 0.5) -> None:
        project_id = self._config_manager.config.get('project').get('id')

        if not project_id:
            self.logger.warning('No project ID set in configuration')
            project_id = ''

        while not self._uplink:
            time.sleep(sleep_time)

        while True:
            payload = {
                'dt': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f'),
                'projectId': project_id
            }

            for target in self._receivers:
                self.publish(target, self._header, payload)

            time.sleep(self._interval)

    def start(self) -> None:
        if self._is_running:
            return

        # self.logger.debug('Starting worker "{}"'
        #                   .format(self._name))
        self._is_running = True
        self._thread = threading.Thread(target=self.run)
        self._thread.daemon = True
        self._thread.start()


class HeartbeatMonitor(Prototype):

    def __init__(self, module_name: str, module_type: str, manager: Manager):
        super().__init__(module_name, module_type, manager)

        # Capture messages of type 'heartbeat'.
        self.add_handler('heartbeat', self.handle_heartbeat)

    def handle_heartbeat(self,
                         header: Dict[str, Any],
                         payload: Dict[str, Any]) -> None:
        pass
