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

from abc import ABCMeta, abstractmethod

logger = logging.getLogger('openadms')


class Prototype(object, metaclass=ABCMeta):
    """Used as a prototype for other modules.
    """

    def __init__(self, name, config_manager):
        self._name = name   # Name of the instance.
        self._config_manager = config_manager

    @abstractmethod
    def action(self, *args):
        """Abstract function that does the action of a module.

        Args:
            *args: Variable length argument list.
        """
        pass

    @abstractmethod
    def destroy(self, *args):
        pass

    @property
    def name(self):
        return self._name
