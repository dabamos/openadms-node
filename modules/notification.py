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

from modules.prototype import Prototype

"""Module for alerting."""


class Alert(Prototype):
    """Alert is used to send warning and error messages to other modules."""

    def __init__(self, name, config_manager, sensor_manager):
        Prototype.__init__(self, name, config_manager, sensor_manager)
        config = self._config_manager.config.get(self._name)

        self._is_enabled = config.get('enabled')
        self._queue = queue.Queue(-1)

        # Add logging handler to the root logger.
        qh = logging.handlers.QueueHandler(self._queue)
        qh.setLevel(logging.WARNING)    # Get WARNING, ERROR, and CRITICAL.
        root = logging.getLogger()
        root.addHandler(qh)

        self._modules = config.get('modules')

        # Check the logging queue continuously for messages and proceed them to
        # the alert agents.
        self._thread = threading.Thread(target=self.run)
        self._thread.daemon = True
        self._thread.start()

    def run(self):
        while True:
            log = self._queue.get()         # Blocking I/O.
            self.logger.info('Processing alert message ...')
            self.fire(log)

    def fire(self, log):
        header = {
            'type': 'alertMessage'
        }

        payload = {
            'dt': log.asctime,
            'level': log.levelname.lower(),
            'message': log.message,
            'receiver': None                # Will be set below.
        }

        # Iterate through the message agent modules.
        for module_name, module in self._modules.items():
            if not module.get('enabled'):
                continue

            receivers = module.get('receivers').get(log.levelname.lower())

            if not receivers or len(receivers) == 0:
                continue

            # Publish a single message for each receiver.
            for receiver in receivers:
                payload['receiver'] = receiver
                self.publish(module_name, header, payload)


class AlertMessageFormatter(Prototype):

    def __init__(self, name, config_manager, sensor_manager):
        Prototype.__init__(self, name, config_manager, sensor_manager)
        self._config = self._config_manager.config.get(self._name)

        # Configuration.
        self._msg_collection_enabled =\
            self._config.get('messageCollectionEnabled')
        self._msg_collection_time = self._config.get('messageCollectionTime')
        self._receiver = self._config.get('receiver')
        self._templates = self._config.get('templates')

        # Message handler.
        self.add_handler('alertMessage', self.handle_alert_message)

        # Queue for alert message collection.
        self._queue = queue.Queue(-1)

        # Threading for alert message collection.
        self._thread = threading.Thread(target=self.run)
        self._thread.daemon = True

        if self._msg_collection_enabled:
            self._thread.start()

    def handle_alert_message(self, header, payload):
        if self._msg_collection_enabled:
            # Add the alert message to the collection queue. It will be
            # processed by the threaded `run()` method later.
            self._queue.put(payload)
        else:
            # Process a single alert message.
            receiver = payload.get('receiver')
            self.process_alert_messages(receiver, [payload])

    def process_alert_messages(self, receiver, messages):
        if not receiver or receiver == '':
            self.logger.warning('No receiver defined for alert message')
            return

        # Create the header of the message.
        header = {
            'type': self._config.get('type')
        }

        # Parse the properties.
        properties = self._config.get('properties')

        for prop_name, prop in properties.items():
            properties[prop_name] = prop.replace('{{receiver}}', receiver)

        # Load the templates
        msg_header = self._templates.get('header')
        msg_footer = self._templates.get('footer')

        # Parse the header and the footer.
        msg_header = msg_header.replace('{{receiver}}', receiver)
        msg_footer = msg_footer.replace('{{receiver}}', receiver)

        # Append the alert messages line by line to the body of the template.
        msg_body = ''

        for msg in messages:
            line = self._templates.get('body')

            for key, value in msg.items():
                line = line.replace('{{' + key + '}}', value)

            # Add the line to the message body.
            msg_body += line

            # Concatenate the message parts.
            complete_msg = ''.join([msg_header,
                                    msg_body,
                                    msg_footer])

            # Create the payload of the message.
            payload = properties
            payload['message'] = complete_msg

            # Fire and forget.
            self.publish(self._receiver, header, payload)

    def run(self, latency=0.5):
        # Dictionary for caching alert messages. Stores a list of dictionaries:
        # '<receiver_name>': [<msg_1>, <msg_2>, ..., <msg_n>]
        cache = {}

        while True:
            try:
                # Get a message from the queue.
                msg = self._queue.get_nowait()

                # Check the receiver.
                receiver = msg.get('receiver')

                if not receiver:
                    self.logger.warning('No receiver defined in alert message')
                else:
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
                        time.sleep(latency)

                # Sleep some time.
                time.sleep(self._msg_collection_time)

                # Clear the messages cache.
                cache.clear()


class MailAgent(Prototype):

    def __init__(self, name, config_manager, sensor_manager):
        Prototype.__init__(self, name, config_manager, sensor_manager)
        config = self._config_manager.config.get(self._name)

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
        self._x_mailer = 'OpenADMS Mail Agent'

        self.add_handler('email', self.handle_mail)

    def handle_mail(self, header, payload):
        if self._is_tls and self._is_start_tls:
            self.logger.error('TLS and StartTLS can\'t be used together')
            return

        mail_subject = payload.get('subject') or self._default_subject
        mail_from = payload.get('from') or self._user_mail
        mail_to = payload.get('to')
        mail_message = payload.get('message')

        self.process_mail(mail_from,
                          mail_to,
                          mail_subject,
                          mail_message)

    def process_mail(self, mail_from, mail_to, mail_subject, mail_message):
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
            # TLS.
            if self._is_tls:
                smtp = smtplib.SMTP_SSL(self._host, self._port)
            else:
                smtp = smtplib.SMTP(self._host, self._port)

            smtp.set_debuglevel(False)
            smtp.ehlo()

            # StartTLS.
            if not self._is_tls and self._is_start_tls:
                smtp.starttls()
                smtp.ehlo()

            smtp.login(self._user_name, self._user_password)
            smtp.sendmail(self._user_mail,
                          [mail_to],
                          msg.as_string())
            smtp.quit()

            self.logger.info('E-mail has been send successfully to {}'
                             .format(mail_to))
        except smtplib.SMTPException:
            self.logger.warning('E-mail could not be sent (SMTP error)')
        except TimeoutError:
            self.logger.warning('E-mail could not be sent (timeout)')


class ShortMessageAgent(Prototype):

    def __init__(self, name, config_manager, sensor_manager):
        Prototype.__init__(self, name, config_manager, sensor_manager)
        config = self._config_manager.config.get(self._name)

        self._host = config.get('host')
        self._port = config.get('port')

        # Capture messages of type "sms".
        self.add_handler('sms', self.handle_short_message)

    def handle_short_message(self, header, payload):
        number = payload.get('number')
        message = payload.get('message')

        if not number:
            self.logger.warning('No phone number defined in short message')
            return

        if not message:
            self.logger.warning('No message text defined in short message')
            return

        self.process_short_message(number, message)

    def process_short_message(self, number, message):
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

                self.logger.info('Sending SMS to "{}" ...'.format(number))
            sock.send(message.encode())

            self.logger.debug('Closed connection to "{}:{}"'
                     .format(self._host, self._port))


class Heartbeat(Prototype):

    def __init__(self, name, config_manager, sensor_manager):
        Prototype.__init__(self, name, config_manager, sensor_manager)
        config = self._config_manager.config.get(self._name)

        self._receivers = config.get('receivers')
        self._interval = config.get('interval')

        self._header = {'type': 'heartbeat'}

        self._thread = threading.Thread(target=self.run)
        self._thread.daemon = True
        self._thread.start()

        self.add_handler('heartbeat', self.process_heartbeat)

    def process_heartbeat(self, header, payload):
        self.logger.info('Received heartbeat at "{}" UTC for project "{}"'
                         .format(payload.get('dt'),
                                 payload.get('projectId')))

    def run(self, sleep_time=0.5):
        project_id = self._config_manager.config.get('project').get('id')

        if not project_id:
            self.logger.warning('No project ID set in configuration')
            project_id = ''

        while not self._uplink:
            time.sleep(sleep_time)

        while True:
            if self._is_paused:
                time.sleep(sleep_time)
                continue

            payload = {
                'dt': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f'),
                'projectId': project_id
            }

            for target in self._receivers:
                self.publish(target, self._header, payload)

            time.sleep(self._interval)


class HeartbeatMonitor(Prototype):

    def __init__(self, name, config_manager, sensor_manager):
        Prototype.__init__(self, name, config_manager, sensor_manager)
        config = self._config_manager.config.get(self._name)

        # Capture messages of type "heartbeat".
        self.add_handler('heartbeat', self.handle_heartbeat)

    def handle_heartbeat(self, header, payload):
        pass
