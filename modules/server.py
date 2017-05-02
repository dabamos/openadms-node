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
from typing import *
from urllib import parse

from core.util import System
from modules.prototype import Prototype


class RequestHandler(BaseHTTPRequestHandler):

    def __init__(self, manager, *args):
        self._config_manager = manager.config_manager
        self._module_manager = manager.module_manager
        self._sensor_manager = manager.sensor_manager

        self._root_dir = '{}/{}'.format(os.getcwd(), 'modules/server')
        self._template = self.get_file_contents(
            self.get_complete_path('/index.html')
        )

        BaseHTTPRequestHandler.__init__(self, *args)

    def do_GET(self) -> None:
        parsed_path = parse.urlparse(self.path)
        file_path = self.get_complete_path(parsed_path.path)

        status = 200
        mime = 'text/html'

        if self.path.endswith('.css'):
            mime = 'text/css'
        elif self.path.endswith('.txt'):
            mime = 'text/plain'

        if parsed_path.path == '/' or parsed_path.path == '/index.html':
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
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()

    def do_action_query(self, query):
        if not self._has_attribute(query, 'action'):
            return

        if not self._has_attribute(query, 'module'):
            return

        module_name = query.get('module')[0]

        if not self._module_manager.has_module(module_name):
            return

        module = self._module_manager.get(module_name)
        action_value = query.get('action')[0]

        if action_value == 'pause' and module.worker.is_running:
            module.stop_worker()

        if action_value == 'start' and not module.worker.is_running:
            module.start_worker()

    def get_404(self) -> str:
        html = ('<!DOCTYPE html><html lang="en">\n'
                '<head><meta charset="utf-8"><title>404</title></head>\n'
                '<body style="background: Linen; font-family: sans-serif;">\n'
                '<h1>Zonk! <small>File not found</small></h1>\n'
                '<p>The file you are looking for cannot be found.</p>\n<hr>\n'
                '<p><small>{openadms_version}</small></p>\n</body></html>'
                .format(openadms_version=System.get_openadms_string())
        )
        return html

    def get_complete_path(self, path) -> Type[Path]:
        return Path('{}/{}'.format(self._root_dir, path))

    def get_file_contents(self, path) -> str:
        with open(path, 'r', encoding='utf-8') as fh:
            file_contents = fh.read()

        return file_contents

    def get_index(self, template) -> str:
        data = {
            'config_file': self._config_manager.path,
            'cpu_load': round(System.get_cpu_load()),
            'hostname': System.get_host_name(),
            'mem_used': round(System.get_used_memory()),
            'modules_list': self.get_modules_list(),
            'openadms_string': System.get_openadms_string(),
            'os_name': System.get_os_name(),
            'python_version': System.get_python_version(),
            'sensors_list': self.get_sensors_list(),
            'system': System.get_system_string(),
            'uptime': System.get_uptime_string()
        }

        return template.format(**data)

    def get_modules_list(self) -> str:
        template = ('<tr><td>{number}</td>'
                    '<td><code>{module_name}</code></td>'
                    '<td><code>{module_type}</code></td>'
                    '<td><span style="color: {color}">{is_running}</span></td>'
                    '<td><a href="/?module={module_name}&action='
                    '{button_action}" class="btn {button_class} sml">'
                    '{button_action}</a></td></tr>\n')
        content = ''
        i = 1

        for module_name, module in self._module_manager.modules.items():
            data = {
                'module_name': module_name,
                'module_type': module.worker.type,
                'number': i
            }

            if module.worker.is_running:
                data['is_running'] = 'running'
                data['color'] = '#52c652'
                data['button_class'] = 'warn'
                data['button_action'] = 'pause'
            else:
                data['is_running'] = 'paused'
                data['color'] = '#f5ad1e'
                data['button_class'] = 'success'
                data['button_action'] = 'start'

            content += template.format(**data)
            i += 1

        return content

    def get_sensors_list(self) -> str:
        template = ('<tr><td>{number}</td>'
                    '<td><code>{sensor_name}</code></td>'
                    '<td><code>{sensor_type}</code></td>'
                    '<td>{sensor_description}</td></tr>\n')
        content = ''
        i = 1

        for sensor_name, sensor in self._sensor_manager.sensors.items():
            data = {
                'number': i,
                'sensor_name': sensor.name,
                'sensor_type': sensor.type,
                'sensor_description': sensor.description
            }

            content += template.format(**data)
            i += 1

        return content

    def _has_attribute(self, query, name):
        if len(query) > 0:
            if query.get(name) or len(query.get(name) > 0):
                return True

        return False

    def log_message(self, format, *args) -> None:
        return

    def respond(self, opts: Dict[str, str]) -> None:
        self.send_response(opts.get('status'))
        self.send_header('Content-type', opts.get('mime'))
        self.end_headers()

        response = bytes(opts.get('content'), 'UTF-8')
        self.wfile.write(response)


class LocalControlServer(Prototype):

    def __init__(self, name, type, manager):
        Prototype.__init__(self, name, type, manager)
        config = self._config_manager.get(self._name)

        self._host = config.get('host')
        self._port = config.get('port')

        def handler(*args): RequestHandler(manager, *args)

        self._httpd = HTTPServer((self._host, self._port), handler)
        self._httpd.serve_forever()

    def __del__(self):
        if self._httpd:
            self._httpd.server_close()
