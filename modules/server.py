#!/usr/bin/env python3.6

"""Module for network services."""

__author__ = 'Philipp Engel'
__copyright__ = 'Copyright (c) 2018 Hochschule Neubrandenburg'
__license__ = 'BSD-2-Clause'

import logging

from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from string import Template
from threading import Thread
from typing import Dict
from urllib import parse

from core.logging import RingBufferLogHandler, RootFilter, StringFormatter
from core.manager import Manager
from core.system import System
from core.prototype import Prototype


class LocalControlServer(Prototype):
    """
    LocalControlServer creates a web service for the remote control of
    OpenADMS. The server shows HTML page with system information and log
    messages. The user can start and stop modules defined in the OpenADMS Node
    configuration. It is recommended to run a reverse proxy in front of the
    LocalControlServer.

    The JSON-based configuration for this module:

    Parameters:
        host (str): FQDN or IP address of the server.
        port (int): Port number.
    """

    def __init__(self, module_name: str, module_type: str, manager: Manager):
        super().__init__(module_name, module_type, manager)
        config = self.get_module_config(self._name)

        self._host = config.get('host')
        self._port = config.get('port')

        self._httpd = None

        # Thread for the HTTP server.
        self._thread = Thread(target=self.run)
        self._thread.daemon = True

        # Store the last 50 log messages of level INFO.
        log_handler = RingBufferLogHandler(logging.INFO, 50)
        log_formatter = StringFormatter()

        log_handler.addFilter(RootFilter())
        log_handler.setFormatter(log_formatter)

        # Add log handler to root handler.
        root = logging.getLogger()
        root.addHandler(log_handler)

        # Custom request handler of the HTTP server.
        def handler(*args):
            RequestHandler(manager, log_handler, *args)

        self._httpd = HTTPServer((self._host, self._port), handler)

    def __del__(self):
        if self._httpd:
            self._httpd.server_close()

    def run(self) -> None:
        """Runs HTTPServer within a thread to avoid blocking."""
        self._httpd.serve_forever()

    def start(self) -> None:
        """Starts the server."""
        if self._is_running:
            return

        super().start()

        # Run HTTP server in thread to avoid blocking.
        self._thread.start()

    def stop(self) -> None:
        """Stops the server."""
        super().stop()

        # Close the HTTP server.
        if self._httpd:
            self._httpd.server_close()


class RequestHandler(BaseHTTPRequestHandler):
    """
    Custom HTTP request handler.
    """

    def __init__(self,
                 manager: Manager,
                 log_handler: RingBufferLogHandler,
                 *args):
        self._config_manager = manager.config_manager
        self._module_manager = manager.module_manager
        self._sensor_manager = manager.sensor_manager
        self._project_manager = manager.project_manager
        self._node_manager = manager.node_manager

        self._log_handler = log_handler
        self._root_dir = 'modules/server'

        index_file = self.absolute_path('/index.html')
        self._template = self.get_file_contents(index_file)

        super().__init__(*args)

    def do_GET(self) -> None:
        """Creates the response to a GET request."""
        parsed_path = parse.urlparse(self.path)
        file_path = self.absolute_path(parsed_path.path)

        status = 200
        mime = 'text/html'

        if self.path.endswith('.css'):
            mime = 'text/css'
        elif self.path.endswith('.txt'):
            mime = 'text/plain'

        if parsed_path.path in ['/', '/index.html']:
            self.do_action_query(parse.parse_qs(parsed_path.query))
            content = self.get_index(self._template)
        else:
            if file_path.exists():
                content = self.get_file_contents(file_path)
            else:
                content = self.get_404()
                status = 404

        self.respond(
            {
                'status': status,
                'mime': mime,
                'content': content
            }
        )

    def do_HEAD(self) -> None:
        """Creates HTTP header."""
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()

    def do_action_query(self, query: Dict) -> None:
        """Processes action query.

        Args:
            query: GET query to process.
        """
        if not self._has_attribute(query, 'action'):
            return

        if not self._has_attribute(query, 'module'):
            return

        module_name = query.get('module')[0]
        action_value = query.get('action')[0]

        if not self._module_manager.has_module(module_name):
            return

        module = self._module_manager.get(module_name)

        if action_value == 'stop' and module.worker.is_running:
            module.stop_worker()

        if action_value == 'start' and not module.worker.is_running:
            module.start_worker()

    def get_404(self) -> str:
        """Returns a "file not found" page (error 404).

        Returns:
            String with HTML page.
        """
        return ('<!DOCTYPE html><html lang="en">\n'
                '<head><meta charset="utf-8"><title>404</title></head>\n'
                '<body style="background: Linen; font-family: sans-serif;">\n'
                '<h1>Zonk! <small>File not found</small></h1>\n'
                '<p>The file you are looking for cannot be found.</p>\n<hr>\n'
                '<p><small>{openadms_version}</small></p>\n</body></html>'
                .format(openadms_version=System.get_openadms_string()))

    def absolute_path(self, path: str) -> Path:
        return Path(self._root_dir + '/' + path)

    def get_file_contents(self, path: Path) -> str:
        """Opens a file and returns the contents.

        Args:
            path: File path.

        Returns:
            String with file contents.
        """
        with open(str(path), 'r', encoding='utf-8') as fh:
            file_contents = fh.read()

        return file_contents

    def get_index(self, template: str) -> str:
        """Returns the index page of this module in HTML format.

        Args:
            template: The template.

        Returns:
            String with the parsed index page.
        """
        vars = {
            'config_file': self._config_manager.path,
            'datetime': System.get_date_time(),
            'hostname': System.get_host_name(),
            'log': self._log_handler.get_logs(),
            'log_size': self._log_handler.size,
            'modules_table': self.get_modules_table(),
            'node_description': self._node_manager.node.description,
            'node_id': self._node_manager.node.id,
            'node_name': self._node_manager.node.name,
            'openadms_string': System.get_openadms_string(),
            'os_name': System.get_os_name(),
            'python_version': System.get_python_version(),
            'project_description': self._project_manager.project.description,
            'project_id': self._project_manager.project.id,
            'project_name': self._project_manager.project.name,
            'root_dir': System.get_root_dir(),
            'sensors_table': self.get_sensors_table(),
            'system': System.get_system_string(),
            'system_uptime': System.get_system_uptime_string(),
            'software_uptime': System.get_software_uptime_string(),
            'year': System.get_current_year()
        }

        return self.parse(template, **vars)

    def get_modules_table(self) -> str:
        """Returns table rows with all modules of the current configuration in
        HTML format. Rather quick and dirty with hard-coded template, but does
        the job.

        Returns:
            String with modules as HTML table rows.
        """
        template = ('<tr><td>$number</td>'
                    '<td><code>$module_name</code></td>'
                    '<td><code>$module_type</code></td>'
                    '<td><span style="color: $color">$status</span></td>'
                    '<td><a href="/?module=$module_name&action='
                    '$button_action" class="btn $button_class sml confirm">'
                    '$button_action</a></td></tr>\n')
        content = ''
        number = 0

        for module_name, module in self._module_manager.modules.items():
            number += 1

            vars = {
                'module_name': module_name,
                'module_type': module.worker.type,
                'number': number
            }

            if module.worker.is_running:
                vars['status'] = 'running'
                vars['color'] = '#52c652'
                vars['button_class'] = 'error'
                vars['button_action'] = 'stop'
            else:
                vars['status'] = 'stopped'
                vars['color'] = '#e93f3c'
                vars['button_class'] = 'success'
                vars['button_action'] = 'start'

            content += self.parse(template, **vars)

        return content

    def get_sensors_table(self) -> str:
        """Returns table rows with all sensors of the current configuration in
        HTML format. Rather quick and dirty with hard-coded template, but does
        the job.

        Returns:
            String with sensors as HTML table rows.
        """
        template = ('<tr><td>$number</td>'
                    '<td><code>$sensor_name</code></td>'
                    '<td><code>$sensor_type</code></td>'
                    '<td>$sensor_description</td></tr>\n')
        content = ''
        number = 0

        for sensor_name, sensor in self._sensor_manager.sensors.items():
            number += 1

            vars = {
                'number': number,
                'sensor_name': sensor.name,
                'sensor_type': sensor.type,
                'sensor_description': sensor.description
            }

            content += self.parse(template, **vars)

        return content

    def _has_attribute(self, query: Dict, name: str) -> bool:
        """Checks a GET query for a given argument.

        Args:
            name: Name of the GET argument.

        Returns:
            True if argument exists, else false.
        """
        if query and query.get(name) and len(query.get(name)) > 0:
            return True

        return False

    def log_message(self, format: str, *args) -> None:
        """Prevents HTTP request handler from adding log messages to the root
        logger."""
        return

    def parse(self, template: str, **kwargs) -> str:
        """Substitutes placeholders in the template with variables from the
        given arguments.

        Args:
            template: The (HTML) template.
            kwargs: The key-value pairs.

        Returns:
            String with parsed template.
        """
        return str(Template(template).safe_substitute(**kwargs))

    def respond(self, opts: Dict[str, str]) -> None:
        """Responds to an HTTP request.

        Args:
            opts: Status code, mime type, return data.
        """
        self.send_response(opts.get('status'))
        self.send_header('Content-type', opts.get('mime'))
        self.end_headers()

        response = bytes(opts.get('content'), 'UTF-8')
        self.wfile.write(response)
