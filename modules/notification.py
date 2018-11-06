#!/usr/bin/env python3.6

"""Module for alerting."""

__author__ = 'Philipp Engel'
__copyright__ = 'Copyright (c) 2017 Hochschule Neubrandenburg'
__license__ = 'BSD-2-Clause'

# Build-in modules.
import logging
import queue
import smtplib
import socket
import ssl
import threading
import time
import uuid

from email.header import Header
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formatdate
from pathlib import Path
from string import Template
from typing import Any, Dict, List

# Third-party modules.
import arrow
from mastodon import Mastodon

# OpenADMS Node modules.
from core.logging import RingBuffer, RootFilter
from core.manager import Manager
from core.system import System
from core.prototype import Prototype


class Alerter(Prototype):
    """
    Alerter is used to send warning and error messages to other modules.

    The JSON-based configuration for this module:

    Parameters:
        is_enabled (bool): If true, alerter is enabled.
        modules (Dict): Modules to send alert messages to.
    """

    def __init__(self, module_name: str, module_type: str, manager: Manager):
        super().__init__(module_name, module_type, manager)
        config = self.get_module_config(self._name)

        self._modules = config.get('modules')
        self._is_enabled = config.get('enabled', True)
        self._thread = None
        self._queue = queue.Queue(1000)

        # Add logging handler to the root logger. Only capture WARNING, ERROR,
        # and CRITICAL.
        qh = logging.handlers.QueueHandler(self._queue)
        qh.addFilter(RootFilter())
        qh.setLevel(logging.WARNING)
        root = logging.getLogger()
        root.addHandler(qh)

        manager.schema.add_schema('alert', 'alert.json')

        if not self._is_enabled:
            self.logger.notice('Alerting is disabled')

    def fire(self, record: logging.LogRecord) -> None:
        # Set the header.
        header = {
            'type': 'alert'
        }

        # Iterate through the message agent modules.
        for module_name, module in self._modules.items():
            if not module.get('enabled'):
                self.logger.notice(f'Skipping module "{module_name}" '
                                   f'(not enabled)')
                continue

            receivers = module.get('receivers').get(record.levelname.lower())

            if not receivers or len(receivers) == 0:
                self.logger.debug(f'No receivers defined for log level '
                                  f'"{record.levelname.lower()}"')
                continue

            # Publish a single message for each receiver.
            for receiver in receivers:
                payload = {
                    'dt': record.asctime,
                    'level': record.levelname.lower(),
                    'name': record.name,
                    'message': record.message,
                    'receiver': receiver
                }

                self.publish(module_name, header, payload)

    def run(self) -> None:
        while self.is_running:
            record = self._queue.get()      # Blocking I/O.
            self.logger.info('Processing alert message')
            self.fire(record)

    def start(self) -> None:
        if self._is_running:
            return

        super().start()

        # Check the logging queue continuously for messages and proceed
        # them to the alert agents.
        self._thread = threading.Thread(target=self.run)
        self._thread.daemon = True
        self._thread.start()


class AlertMessageFormatter(Prototype):
    """
    AlertMessageFormatter caches and formats alerts. They are then forwarded to
    other modules for further processing and transmission.

    Parameters:
        messageCollectionEnabled (bool): If true, cache alert messages.
        messageCollectionTime (float): Time to cache messages before sending.
        properties (Dict): Additional properties to add to the message.
        receiver (str): Name of the receiving module.
        templates (Dict): Templates for `header`, `body`, and `footer`.
        type (str): Type of the message to be send (`email`, `sms`, etc.).
    """

    def __init__(self, module_name: str, module_type: str, manager: Manager):
        super().__init__(module_name, module_type, manager)
        self._config = self.get_module_config(self._name)
        self._thread = None

        # Configuration.
        self._msg_collection_enabled =\
            self._config.get('messageCollectionEnabled')
        self._msg_collection_time = self._config.get('messageCollectionTime')
        self._receiver = self._config.get('receiver')
        self._templates = self._config.get('templates')

        # Message handler.
        self.add_handler('alert', self.handle_alert_message)

        # Queue for alert message caching.
        self._queue = queue.Queue(-1)

    def handle_alert_message(self,
                             header: Dict[str, Any],
                             payload: Dict[str, Any]) -> None:
        """Handles messages of type `alert` and either caches them or forwards
        them to the `process_alert_messages()` method.

        Args:
            header: The alert header.
            payload: The alert payload.
        """
        if self._msg_collection_enabled:
            # Cache the alert message. It will be processed by the threaded
            # `run()` method later.
            self._queue.put(payload)
        else:
            # Process a single alert message immediately.
            receiver = payload.get('receiver')
            self.process_alert_messages(receiver, [payload])

    def process_alert_messages(self,
                               receiver: str,
                               alerts: List[Dict[str, str]]) -> None:
        """Parses a template and fills values of an alert message into header,
        body, and footer. The parsed template is forwarded to an agent (e-mail,
        SMS, ...).

        Args:
            receiver: The receiver of the alert.
            alerts: The list of alert messages.
        """
        if not receiver or receiver == '':
            self.logger.warning('No receiver defined for alert message')
            return

        # Create the header of the message.
        header = {
            'type': self._config.get('type')
        }

        # Parse the properties and replace placeholders.
        properties = {}

        vars = {
            'nid': self._node_manager.node.id,              # Sensor node ID.
            'node': self._node_manager.node.name,           # Sensor node name.
            'pid': self._project_manager.project.id,        # Project ID.
            'project': self._project_manager.project.name,  # Project name.
            'receiver': receiver                            # Name of receiver.
        }

        for prop_name, prop in self._config.get('properties').items():
            for var_name, var in vars.items():
                properties[prop_name] = prop.replace('{{' + var_name + '}}',
                                                     var)

        # Load the templates
        msg_header = self._templates.get('header', '')
        msg_footer = self._templates.get('footer', '')

        # Parse the header and the footer.
        for var_name, var in vars.items():
            msg_header = msg_header.replace('{{' + var_name + '}}', var)
            msg_footer = msg_footer.replace('{{' + var_name + '}}', var)

        # Append the alert messages line by line to the body of the template.
        msg_body = ''

        for alert in alerts:
            line = self._templates.get('body', '')

            for key, value in alert.items():
                line = line.replace('{{' + key + '}}', value)

            for var_name, var in vars.items():
                line = line.replace('{{' + var_name + '}}', var)

            msg_body += line

        # Concatenate the message parts.
        complete_msg = ''.join([msg_header, msg_body, msg_footer])

        # Create the payload of the message.
        payload = properties
        payload['message'] = complete_msg

        # Fire and forget.
        self.logger.debug(f'Sending formatted alert message to '
                          f'"{self._receiver}"')
        self.publish(self._receiver, header, payload)

    def run(self) -> None:
        """Processes the cached alert messages."""
        # Dictionary for caching alert messages. Stores a list of dictionaries:
        # '<receiver_name>': [<dict_1>, <dict_2>, ..., <dict_n>]
        cache = {}

        while self._is_running:
            try:
                # Get a message from the queue.
                msg = self._queue.get_nowait()
                # Check the receiver.
                receiver = msg.get('receiver')

                if not receiver:
                    raise ValueError('No receiver defined in alert message')

                # Create an empty list for the alert messages.
                if not cache.get(receiver):
                    cache[receiver] = []

                # Append the message to the list of the receiver.
                cache[receiver].append(msg)
            except queue.Empty:
                if len(cache) > 0:
                    for receiver, messages in cache.items():
                        if not messages or len(messages) == 0:
                            # No messages for receiver.
                            continue

                        self.process_alert_messages(receiver, messages)

                # Sleep some time.
                self.logger.debug(f'Waiting {self._msg_collection_time} s')
                time.sleep(self._msg_collection_time)

                # Clear the messages cache.
                cache.clear()

    def start(self) -> None:
        if self._is_running:
            return

        super().start()

        if self._msg_collection_enabled:
            # Threading for alert message caching.
            self._thread = threading.Thread(target=self.run)
            self._thread.daemon = True
            self._thread.start()


class Heartbeat(Prototype):
    """
    Heartbeat sends heartbeat messages ("pings") to the message broker by using
    the message type `heartbeat`.

    The JSON-based configuration for this module:

    Parameters:
        interval (float): Interval for sending heartbeats.
        receivers (List): List of topics to send heartbeats to.
    """

    def __init__(self, module_name: str, module_type: str, manager: Manager):
        super().__init__(module_name, module_type, manager)
        config = self._config_manager.get(self._name)

        self._receivers = config.get('receivers')
        self._interval = config.get('interval')

        self._thread = None
        self._header = { 'type': 'heartbeat' }

        self.add_handler('heartbeat', self.process_heartbeat)

    def process_heartbeat(self,
                          header: Dict[str, Any],
                          payload: Dict[str, Any]) -> None:
        self.logger.info(f'Received heartbeat at "{payload.get("dt")}" UTC '
                         f'for project "{payload.get("project")}"')

    def run(self) -> None:
        project_id = self._project_manager.project.id

        while True:
            payload = {
                'dt': arrow.utcnow(),
                'pid': project_id
            }

            for target in self._receivers:
                self.publish(target, self._header, payload)

            time.sleep(self._interval)

    def start(self) -> None:
        if self._is_running:
            return

        super().start()

        self._thread = threading.Thread(target=self.run)
        self._thread.daemon = True
        self._thread.start()


class IrcAgent(Prototype):
    """
    IrcAgent sends alert messages to the Internet Relay Chat. This module acts
    as a simple IRC bot which connects to an IRC server and sends text messages
    to a channel or user. Only a few commands of RFC 1459 are implemented.

    The JSON-based configuration for this module:

    Parameters:
        channel (str): IRC channel to join (e.g.: ``#test``).
        host (str): FQDN or IP address of IRC server.
        port (int): Port number of IRC server.
        is_tls (bool): If true, use TLS encryption.
        nickname (str): Nickname to use (default: ``openadms``).
        password (str): Password of registered nickname (optional).
        target (str): IRC channel or user to send messages to.
    """

    def __init__(self, module_name: str, module_type: str, manager: Manager):
        super().__init__(module_name, module_type, manager)

        self._conn = None
        self._thread = None
        self._queue = queue.Queue(-1)

        config = self.get_module_config(self._name)
        self._host = config.get('server')
        self._port = config.get('port', 6667)
        self._is_tls = config.get('tls', False)
        self._nickname = config.get('nickname', 'openadms')
        self._password = config.get('password')
        self._target = config.get('target')
        self._channel = config.get('channel')

        if not self._channel.startswith('#'):
            self.logger.warning('Channel name doesn\'t start with "#"')
            self._channel = '#' + self._channel

        self.add_handler('irc', self.handle_irc)
        manager.schema.add_schema('irc', 'irc.json')

    def __del__(self):
        self._disconnect()

    def _connect(self, is_tls: bool = False) -> None:
        """Creates socket connection to IRC server.

        Args:
            is_tls: If True, use TLS-encrypted connection.
        """
        self._disconnect()
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        if is_tls:
            # Create SSL context for secured socket connection to IRC server.
            context = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
            context.load_default_certs()
            self._conn = context.wrap_socket(sock,
                                             server_hostname=self._host)
        else:
            self._conn = sock

        self.logger.info(f'Connecting to "{self._host}:{self._port}" ...')

        try:
            # Connect to IRC server.
            self._conn.connect((self._host, self._port))
            self._conn.setblocking(0)
            self._conn.settimeout(1)
        except ConnectionRefusedError:
            self.logger.error(f'Could not connect to "{self._host}:'
                              f'{self._port}" (connection refused)')
        except TimeoutError:
            self.logger.error(f'Could not connect to "{self._host}:'
                              f'{self._port}" (timeout)')
        except ssl.SSLError:
            self.logger.error(f'Could not connect to "{self._host}:'
                              f'{self._port}" (SSL error)')

    def _disconnect(self) -> None:
        """Disconnects from IRC server and closes socket connection."""
        if self._conn:
            self._send('QUIT\r\n')
            self._conn.close()
            self._conn = None

    def handle_irc(self,
                   header: Dict[str, Any],
                   payload: Dict[str, Any]) -> None:
        """Handles messages of type `irc` and puts alert message on a queue.

        Args:
            header: The message header.
            payload: The message payload.
        """
        self._queue.put(payload)

    def _init(self) -> None:
        """Enters IRC server and joins channel."""
        self._receive()

        if self._password and len(self._password) > 0:
            self._send(f'PASS {self._password}\r\n')

        self._send(f'NICK {self._nickname}\r\n')
        self._send(f'USER {self._nickname} {self._nickname} {self._nickname} '
                   f':OpenADMS Node IRC Client\r\n')

        if self._channel and len(self._channel) > 0:
            self.logger.info(f'Joining channel "{self._channel}" on '
                             f'"{self._host}:{self._port}" ...')
            self._send(f'JOIN {self._channel}\r\n')

    def _priv_msg(self, target: str, message: str) -> None:
        """Sends message to channel or user.

        Args:
            target: The channel or user name.
            message: The message to send.
        """
        self._send(f'PRIVMSG {target} :{message}\r\n')

    def _receive(self, buffer_size: int = 4096) -> str:
        """Receives message from server.

        Args:
            buffer_size: The buffer size.

        Returns:
            String with the message.
        """
        message = ''

        try:
            message = self._conn.recv(buffer_size).decode('utf-8')
        except Exception:
            pass

        return message

    def run(self) -> None:
        """Connects to IRC server, enters channel, and sends messages. Reacts
        to PING messages by the server."""
        while self._is_running:
            if not self._conn:
                self._connect(self._is_tls)
                self._init()

            data = self._receive()

            if data.startswith('PING'):
                self._send(f'PONG {data.split()[1]}\r\n')

            if not self._queue.empty():
                item = self._queue.get()
                target = item.get('target', self._target)
                message = item.get('message', '')

                self._priv_msg(target, message)
                self.logger.debug(f'Sent alert message to target "{target}" on '
                                  f'network "{self._host}:{self._port}"')

        self._disconnect()

    def _send(self, message: str) -> None:
        """Sends message to server.

        Args:
            message: The message string.
        """
        self._conn.send(message.encode('utf-8'))

    def start(self) -> None:
        if self._is_running:
            return

        super().start()

        self._thread = threading.Thread(target=self.run)
        self._thread.daemon = True
        self._thread.start()


class MailAgent(Prototype):
    """
    MailAgents sends e-mails via SMTP.

    The JSON-based configuration for this module:

    Parameters:
        retryDelay (float): Time to wait before resending after failure.
        charset (str): Character set of the email.
        defaultSubject (str): Default subject if no subject is given.
        host (str): FQDN or IP address of the SMTP server.
        startTls (bool): If true, use StartTLS encryption.
        tls (bool): If true, use TLS encryption.
        port (int): Port number of the SMTP server.
        userMail (str): Email address of the sender.
        userName (str): SMTP user name.
        userPassword (str): SMTP user password.
    """

    def __init__(self, module_name: str, module_type: str, manager: Manager):
        super().__init__(module_name, module_type, manager)
        config = self.get_module_config(self._name)

        self._retry_delay = config.get('retryDelay') or 600.0
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
        self._x_mailer = f'OpenADMS Node {System.get_openadms_version()}'

        if self._is_tls and self._is_start_tls:
            raise ValueError('Invalid SSL configuration '
                             '(select either TLS or StartTLS)')

        self.add_handler('email', self.handle_mail)
        manager.schema.add_schema('email', 'email.json')

    def handle_mail(self,
                    header: Dict[str, Any],
                    payload: Dict[str, Any]) -> None:
        """Handles messages of type `email` and forwards them to the
        `process_mail()` method.

        Args:
            header: The message header.
            payload: The message payload.
        """
        mail_subject = payload.get('subject', self._default_subject)
        mail_from = payload.get('from', self._user_mail)
        mail_to = payload.get('to', '')
        mail_message = payload.get('message', '')

        self.process_mail(mail_from,
                          mail_to,
                          mail_subject,
                          mail_message)

    def process_mail(self,
                     mail_from: str,
                     mail_to: str,
                     mail_subject: str,
                     mail_message: str) -> None:
        """Sends e-mails by SMTP.

        Args:
            mail_from: The sender of the email.
            mail_to: The recipient of the email.
            mail_subject: The subject of the email.
            mail_message: The body text of the email.
        """
        msg = MIMEMultipart('alternative')
        msg['From'] = f'{mail_from} <{self._user_mail}>'
        msg['To'] = mail_to
        msg['Date'] = formatdate(localtime=True)
        msg['X-Mailer'] = self._x_mailer
        msg['Subject'] = Header(mail_subject, self._charset)

        plain_text = MIMEText(mail_message.encode(self._charset),
                              'plain',
                              self._charset)
        msg.attach(plain_text)

        done = False

        # Repeat in case of error.
        while not done:
            try:
                if self._is_tls and not self._is_start_tls:
                    # Use TLS encryption.
                    smtp = smtplib.SMTP_SSL(self._host, self._port)
                else:
                    # Use no or StartTLS encryption.
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

                done = True
                self.logger.info(f'E-mail has been send successfully to '
                                 f'"{mail_to}"')
            except smtplib.ConnectionResetError:
                self.logger.warning(f'E-mail could not be sent to "{mail_to}" '
                                    f'(connection reset by peer)')
                time.sleep(self._retry_delay)
            except smtplib.SMTPException:
                self.logger.warning(f'E-mail could not be sent to "{mail_to}" '
                                    f'(SMTP error)')
                time.sleep(self._retry_delay)
            except socket.gaierror:
                self.logger.warning(f'E-mail could not be sent to "{mail_to}"'
                                    f'(connection error)')
                time.sleep(self._retry_delay)
            except TimeoutError:
                self.logger.warning(f'E-mail could not be sent to "{mail_to}" '
                                    f'(timeout)')
                time.sleep(self._retry_delay)


class MastodonAgent(Prototype):
    """
    Mastodon sends toots to the Mastodon social network. Requires the Python
    module `Mastodon.py`.

    The JSON-based configuration for this module:

    Parameters:
        email (str): Login email address of Mastodon account.
        password (str): Login password of Mastodon account.
        url (str): URL of the Mastodon instance (e.g.: `https://mastodon.at`).
    """

    def __init__(self, module_name: str, module_type: str, manager: Manager):
        super().__init__(module_name, module_type, manager)
        config = self.get_module_config(self._name)

        self.add_handler('mastodon', self.handle_mastodon)
        manager.schema.add_schema('mastodon', 'mastodon.json')

        self._email = config.get('email')
        self._password = config.get('password')
        self._api_base_url = config.get('url', 'https://mastodon.social')

        self._client_cred_file = 'mastodon_client_cred.secret'
        self._user_cred_file = 'mastodon_user_cred.secret'

        self._mastodon = None

    def _create_app(self) -> None:
        Mastodon.create_app('openadms',
                            api_base_url=self._api_base_url,
                            to_file='openadms_clientcred.secret')
        self.logger.debug('Created client application')

    def _login(self) -> None:
        try:
            self._mastodon.log_in(self._email,
                                  self._password,
                                  to_file=self._user_cred_file)
            self.logger.debug(f'Login on "{self._api_base_url}" was successful')
        except Exception:
            self.logger.error(f'Can\'t login on "{self._api_base_url}"')

    def handle_mastodon(self,
                        header: Dict[str, Any],
                        payload: Dict[str, Any]) -> None:
        """Uses the Mastodon API to send toots to the network.

        Args:
            header: The message header.
            payload: The message payload.
        """
        if not Path(self._client_cred_file).exists():
            self._create_app()

        if not self._mastodon:
            self._mastodon = Mastodon(client_id=self._client_cred_file,
                                      api_base_url=self._api_base_url)

        message = payload.get('message')

        if message and len(message) > 0:
            try:
                self._login()
                self._mastodon.toot(message)
                self.logger.info(f'Tooted to "{self._api_base_url}"')
            except Exception:
                self.logger.error(f'Can\'t access "{self._api_base_url}"')


class RssAgent(Prototype):
    """
    RSSAgent creates an RSS 2.0 feed out of given data.

    The JSON-based configuration for this module:

    Parameters:
        author (str): Author of the RSS feed.
        description (str): Description text of the RSS feed.
        language (str): Language of the RSS feed (e.g.: `en-gb`).
        link (str): URL to the RSS feed.
        size (int): Number of entries in the RSS feed.
        title (str): Title of the RSS feed.
    """

    def __init__(self, module_name: str, module_type: str, manager: Manager):
        super().__init__(module_name, module_type, manager)
        config = self.get_module_config(self._name)

        self._size = config.get('size', 25)
        self._ring_buffer = RingBuffer(self._size)
        self._default_title = '[OpenADMS] Alert Message'
        self._file_path = Path(config.get('filePath'))

        self._vars = {
            'author': config.get('author', System.get_openadms_string()),
            'description': config.get('description',
                                      'OpenADMS Alert Messages RSS Feed'),
            'language': config.get('language', 'en-gb'),
            'link': config.get('link', ''),
            'title': config.get('title', 'OpenADMS RSS Feed'),
            'version': System.get_openadms_version()
        }

        self.add_handler('rss', self.handle_rss)
        manager.schema.add_schema('rss', 'rss.json')

    def escape(self, html: str) -> str:
        """Returns the given HTML with ampersands, quotes, and carets
        encoded.

        Args:
            html: String with HTML special characters.

        Returns:
            Escaped string.
        """
        return html.replace('&', '&amp;')\
                   .replace('<', '&lt;')\
                   .replace('>', '&gt;')\
                   .replace('"', '&quot;')\
                   .replace("'", '&#39;')

    def handle_rss(self,
                   header: Dict[str, Any],
                   payload: Dict[str, Any]) -> None:
        """Handles messages of type `rss` and forwards them to the
        `process_rss()` method.

        Args:
            header: The message header.
            payload: The message payload.
        """
        # Add default values.
        if not payload.get('author'):
            payload['author'] = self._vars.get('author')

        if not payload.get('dt'):
            payload['dt'] = str(arrow.utcnow())

        if not payload.get('description'):
            payload['description'] = ''

        if not payload.get('guid'):
            payload['guid'] = f'urn:uuid:{uuid.uuid4()}'

        if not payload.get('title'):
            payload['title'] = self._default_title

        # Convert UTC date to RFC 822 format.
        dt = payload.get('dt', str(arrow.utcnow()))
        payload['dt'] = self.rfc_822(dt)

        self._ring_buffer.append(payload)
        rss = self.get_rss_feed(self._vars, self._ring_buffer.list())
        self.write(self._file_path, rss)

    def get_rss_feed(self,
                     vars: Dict[str, str],
                     items: List[Dict[str, str]]) -> str:
        """Returns a string with the RSS 2.0 feed. Feed template is hard-coded
        into this method. Rather quick and dirty, but does the job.

        Args:
            vars: The variables to replace in the RSS template.
            items: The items of the RSS feeds.

        Returns:
            The RSS 2.0 feed as a string.
        """
        # Create the RSS items.
        item_tpl = ('        <item>\n'
                    '            <title>$title</title>\n'
                    '            <description>$message</description>\n'
                    '            <author>$author</author>\n'
                    '            <guid isPermaLink="false">$guid</guid>\n'
                    '            <pubDate>$dt</pubDate>\n'
                    '            <link>$link</link>\n'
                    '        </item>\n\n')
        rss_items = ''

        # Parse item template.
        for item in items:
            rss_items += self.parse(item_tpl, **item)

        # Create the RSS feed.
        vars['date'] = self.rfc_822()
        vars['items'] = rss_items

        rss_tpl = ('<?xml version="1.0" encoding="utf-8" ?>\n'
                   '<rss version="2.0" '
                   'xmlns:atom="http://www.w3.org/2005/Atom">\n'
                   '    <channel>\n'
                   '        <title>$title</title>\n'
                   '        <description>$description</description>\n'
                   '        <language>$language</language>\n'
                   '        <link>$link</link>\n'
                   '        <copyright>$author</copyright>\n'
                   '        <pubDate>$date</pubDate>\n'
                   '        <atom:link rel="self" href="$link" '
                   'type="application/rss+xml"/>\n\n'
                   '$items'
                   '    </channel>\n'
                   '</rss>')
        rss = self.parse(rss_tpl, **vars)

        return rss

    def parse(self, template: str, **kwargs) -> str:
        """Substitutes placeholders in the template with variables from the
        given arguments.

        Args:
            template: The template.
            kwargs: The key-value pairs.

        Returns:
            String with parsed template.
        """
        return str(Template(template).safe_substitute(**kwargs))

    def rfc_822(self, date: str = None) -> str:
        """Returns a date string formatted as RFC 822. If no date is given, the
        current date is used.

        Args:
            date: A string with date and time in UTC.

        Returns:
            A string with of date and time as RFC 822.
        """
        if not date or date == '':
            date = str(arrow.utcnow())

        return str(arrow.get(date).format('ddd, DD MMM YYYY HH:mm:ss Z'))

    def write(self, file_path: Path, contents: str) -> None:
        """Writes string to file."""
        if not file_path:
            self.logger.error('No file path set')
            return

        if not contents:
            self.logger.error('No contents to write')
            return

        with open(str(file_path), 'w') as fh:
            fh.write(contents)
            self.logger.info(f'Saved RSS feed to file "{str(file_path)}"')


class ShortMessageAgent(Prototype):
    """
    ShortMessageAgent uses a socket connection to a GSM modem to send SMS.

    The JSON-based configuration for this module:

    Parameters:
        host (str): FQDN or IP address of the SMS server.
        port (int): Port number of the SMS server.
    """

    def __init__(self, module_name: str, module_type: str, manager: Manager):
        super().__init__(module_name, module_type, manager)
        config = self.get_module_config(self._name)

        self._host = config.get('host')
        self._port = config.get('port')

        # Capture messages of type `sms`.
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
                self.logger.debug(f'Connection to "{self._host}:{self._port}" '
                                  f'has been established')
            except ConnectionRefusedError:
                self.logger.error(f'Could not connect to "{self._host}:'
                                  f'{self._port}" (connection refused)')
                return
            except TimeoutError:
                self.logger.error(f'Could not connect to "{self._host}:'
                                  f'{self._port}" (timeout)')
                return

            self.logger.info(f'Sending SMS to "{number}" ...')
            sock.send(message.encode())
            self.logger.debug(f'Closed connection to "{self._host}:'
                              f'{self._port}"')


class StatusPublisher(Prototype):
    """
    StatusPublisher sends retained messages to a given topic of the MQTT server.
    The messages include project, node, and system information, current uptime,
    loaded modules and sensors, and current timestamp.

    The JSON-based configuration for this module:

    Parameters:
        topic (str): MQTT topic to publish to.
        interval (int): Interval of status messages.
    """

    def __init__(self, module_name: str, module_type: str, manager: Manager):
        super().__init__(module_name, module_type, manager)

        self._thread = None
        self._header = {'type': 'status'}

        config = self.get_module_config(self._name)
        self._topic = config.get('topic')
        self._interval = config.get('interval')

        manager.schema.add_schema('status', 'status.json')

    def _get_modules(self) -> List[Dict]:
        modules = []

        for module_name, module in self._module_manager.modules.items():
            modules.append({
                'name': module_name,
                'type': module.worker.type,
                'status': 'running' if module.worker.is_running else
                          'stopped'
            })

        return modules

    def _get_sensors(self) -> List[Dict]:
        sensors = []

        for sensor_name, sensor in self._sensor_manager.sensors.items():
            sensors.append({
                'name': sensor.name,
                'type': sensor.type,
                'description': sensor.description
            })

        return sensors

    def run(self) -> None:
        while self._is_running:
            payload = {
                'modules': self._get_modules(),
                'node': {
                    'description': self._node_manager.node.description,
                    'id': self._node_manager.node.id,
                    'name': self._node_manager.node.name
                },
                'project': {
                    'description': self._project_manager.project.description,
                    'id': self._project_manager.project.id,
                    'name': self._project_manager.project.name
                },
                'sensors': self._get_sensors(),
                'statistics': {
                    'softwareUptime': System.get_software_uptime_string(),
                    'systemUptime': System.get_system_uptime_string()
                },
                'system': {
                    'configFile': self._config_manager.path,
                    'datetime': System.get_date_time(),
                    'host': System.get_host_name(),
                    'interpreter': System.get_python_version(),
                    'os': System.get_system_string(),
                    'rootDirectory': str(System.get_root_dir()),
                    'version': System.get_openadms_string(),
                },
                'timestamp': str(arrow.utcnow()),
                'type': 'status'
            }

            self.logger.debug(f'Sending status message to topic '
                              f'"{self._topic}" ...')
            self.publish(self._topic, self._header, payload, retain=True)
            time.sleep(self._interval)

    def start(self) -> None:
        if self._is_running:
            return

        super().start()

        self._thread = threading.Thread(target=self.run)
        self._thread.daemon = True
        self._thread.start()
