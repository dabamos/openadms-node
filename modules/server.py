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

__author__ = 'Philipp Engel'
__copyright__ = 'Copyright (c) 2017 Hochschule Neubrandenburg'
__license__ = 'EUPL'

import os

from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

from core.util import System
from modules.prototype import Prototype


class RequestHandler(BaseHTTPRequestHandler):

    def __init__(self, managers, *args):
        self._config_manager = managers.config_manager
        self._module_manager = managers.module_manager

        root = '/modules/server'
        self._root_dir = '{}{}'.format(os.getcwd(), root)

        BaseHTTPRequestHandler.__init__(self, *args)

    def do_GET(self):
        mime_type = 'text/html'

        if self.path.endswith('.css'):
            mime_type = 'text/css'

        self.respond({'status': 200, 'mime': mime_type})

    def do_HEAD(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()

    def get_file(self, path):
        file_path = '{}/{}'.format(self._root_dir, path)

        with open(file_path, 'r', encoding='utf-8') as fh:
            file_content = fh.read()

        return file_content

    def get_index(self):
        data = {
            'config_file': self._config_manager.path,
            'cpu_load': round(System.get_cpu_load()),
            'hostname': System.get_host_name(),
            'mem_used': round(System.get_used_memory()),
            'openadms_version': System.get_openadms_version(),
            'openadms_version_name': System.get_openadms_version_name(),
            'os_name': System.get_os_name(),
            'python_version': System.get_python_version(),
            'system': System.get_system_string(),
            'uptime': System.get_uptime_string()
        }

        template_file = self.get_file('/index.html')
        parsed = template_file.format(**data)

        return parsed

    def log_message(self, format, *args):
        return

    def respond(self, opts):
        self.send_response(opts.get('status'))
        self.send_header('Content-type', opts.get('mime'))
        self.end_headers()

        if self.path == '/':
            content = self.get_index()
        else:
            content = self.get_file(self.path)

        if content:
            response = bytes(content, 'UTF-8')
            self.wfile.write(response)


class LocalControlServer(Prototype):

    def __init__(self, name, type, managers):
        Prototype.__init__(self, name, type, managers)
        config = self._config_manager.get(self._name)

        self._host = config.get('host')
        self._port = config.get('port')

        def handler(*args): RequestHandler(managers, *args)

        self._httpd = HTTPServer((self._host, self._port), handler)
        self._httpd.serve_forever()

    def __del__(self):
        if self._httpd:
            self._httpd.server_close()
