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
import smtplib
import socket
import threading
import time

from abc import ABCMeta, abstractmethod
from email.header import Header
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formatdate
from queue import Queue

from modules.prototype import Prototype

"""Module for alerting."""

logger = logging.getLogger('openadms')


class Alert(Prototype):
    """Alert is used to send warning and error messages by e-mail or SMS."""

    def __init__(self, name, config_manager, sensor_manager):
        Prototype.__init__(self, name, config_manager, sensor_manager)
        config = self._config_manager.config.get(self._name)

        self._enabled = config.get('Enabled')
        self._queue = queue.Queue(-1)
        self._alert_handlers = []

        # Add logging handler to the logger.
        qh = logging.handlers.QueueHandler(self._queue)
        qh.setLevel(logging.WARNING)    # Get WARNING, ERROR, and CRITICAL.
        logger.addHandler(qh)

        # Add the alert handlers to the alert handlers list.
        handlers = config.get('Handlers')

        for handler in handlers:
            if handlers.get(handler).get('Enabled') is False:
                continue

            # Add handler to the handlers list.
            handler_class = globals().get(handler)

            if handler_class:
                config = handlers.get(handler)
                handler_instance = handler_class(config)
                self._alert_handlers.append(handler_instance)
                logger.debug('Loaded alert handler "{}"'.format(handler))
            else:
                logger.warning('Alert handler "{}" not found'.format(handler))

        # Check the logging queue continuously for messages and proceed them to
        # the alert handlers.
        self._thread = threading.Thread(target=self.process_alert)
        self._thread.daemon = True
        self._thread.start()

    def process_alert(self):
        if self._enabled:
            while True:
                # Blocking I/O.
                record = self._queue.get()
                logger.info('Processing alert message ...')

                for alert_handler in self._alert_handlers:
                    alert_handler.handle(record)


class AlertHandler(object):

    __metaclass__ = ABCMeta

    def __init__(self, config):
        self._config = config

    @abstractmethod
    def handle(self, record):
        pass


class ShortMessageSocketAlertHandler(AlertHandler):

    def __init__(self, config):
        AlertHandler.__init__(self, config)

        self._enabled = self._config.get('Enabled')
        self._log_levels = [x.upper() for x in self._config.get('LogLevels')]
        self._host = self._config.get('Host')
        self._port = self._config.get('Port')
        self._phone_numbers = self._config.get('PhoneNumbers')
        self._template = self._config.get('Template')

        self._msg_vars = {}
        self._last_message = ''

    def add_var(self, key, value):
        self._msg_vars['{' + key + '}'] = value

    def handle(self, record):
        if not self._enabled:
            return

        if record.levelname not in self._log_levels:
            return

        # Do not send message if it equals the last one.
        if record.message == self._last_message:
            logger.debug('Skipped sending alert message (message equals '
                         'last message)')
            return

        self._last_message = record.message

        self.add_var('asctime', record.asctime)
        self.add_var('level', record.levelname)
        self.add_var('msg', record.message)

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            try:
                sock.connect((self._host, self._port))
                logger.debug('Established connection to "{}:{}"'
                             .format(self._host, self._port))
            except ConnectionRefusedError:
                logger.error('Could not connect to "{}:{}" (connection refused)'
                             .format(self._host, self._port))
                return
            except TimeoutError:
                logger.error('Could not connect to "{}:{}" (timeout)'
                             .format(self._host, self._port))
                return

            for number in self._phone_numbers:
                text = self._template
                self.add_var('number', number)

                for key, value in self._msg_vars.items():
                    text = text.replace(key, value)

                logger.info('Sending SMS to "{}" ...'.format(number))
                sock.send(text.encode())
                time.sleep(1.0)

        logger.debug('Closed connection to "{}:{}"'
                     .format(self._host, self._port))


class MailAlertHandler(AlertHandler):

    def __init__(self, config):
        AlertHandler.__init__(self, config)

        self._enabled = self._config.get('Enabled')
        self._collection_time = self._config.get('CollectionTime')
        self._log_levels = [x.upper() for x in self._config.get('LogLevels')]
        self._recipients = self._config.get('Recipients')
        self._subject = self._config.get('Subject') or '[OpenADMS] Notification'
        self._charset = self._config.get('Charset')

        self._user_name = self._config.get('UserName')
        self._user_password = self._config.get('UserPassword')
        self._host = self._config.get('Host')
        self._port = self._config.get('Port')

        tls = self._config.get('TLS')

        if tls.lower() in ['yes', 'no', 'starttls']:
            self._tls = tls.lower()

        self._queue = Queue(-1)

        self._thread = threading.Thread(target=self.run)
        self._thread.daemon = True
        self._thread.start()

    def handle(self, record):
        if not self._enabled:
            return

        if record.levelname not in self._log_levels:
            return

        self._queue.put(record)

    def run(self):
        while True:
            records = []

            try:
                record = self._queue.get_nowait()
                records.append(record)
            except Queue.Empty:
                if len(messages) > 0:
                    self.send_all(records)

                time.sleep(self._collection_time)


    def send_all(self, records):
        text = 'The following incident(s) occurred:\n\n'

        for record in records:
            text += ' - '.join([record.asctime,
                                record.levelname,
                                record.message])

        text += '\n\nPlease do not reply as this e-mail was sent from an ' \
                'automated alerting system.'

        msg = MIMEMultipart('alternative')

        msg['From'] = self._user_name
        msg['To'] = ', '.join(self._recipients)
        msg['Date'] = formatdate(localtime=True)
        msg['X-Mailer'] = 'OpenADMS Mail Alert Handler'
        msg['Subject'] = Header(self._subject, self._charset)

        plain_text = MIMEText(text.encode(self._charset),
                              'plain',
                              self._charset)

        msg.attach(plain_text)

        try:
            if self._tls == 'yes':
                smtp = smtplib.SMTP_SSL(self._host, self._port)
            else:
                smtp = smtplib.SMTP(self._host, self._port)

            smtp.set_debuglevel(False)
            smtp.ehlo()

            if self._tls == 'starttls':
                smtp.starttls()
                smtp.ehlo()

            smtp.login(self._user_name, self._user_password)
            smtp.sendmail(self._user_name, self._recipients, msg.as_string())
            smtp.quit()

            logger.info('E-mail has been send successfully to {}'
                        .format(', '.join(self._recipients)))
        except smtplib.SMTPException:
            logger.warning('E-mail could not be sent (SMTP error)')
        except TimeoutError:
            logger.warning('E-mail could not be sent (timeout)')


class Heartbeat(Prototype):

    def __init__(self, name, config_manager, sensor_manager):
        Prototype.__init__(self, name, config_manager, sensor_manager)
        config = self._config_manager.config.get(self._name)

        self._handlers['Heartbeat'] = self.handle_heartbeat

    def handle_heartbeat(self, header, payload):
        pass


