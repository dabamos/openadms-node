#!/usr/bin/env python3
'''
Copyright (c) 2017 Hochschule Neubrandenburg.

Licensed under the EUPL, Version 1.1 or - as soon they will be approved
by the European Commission - subsequent versions of the EUPL (the
'Licence');

You may not use this work except in compliance with the Licence.

You may obtain a copy of the Licence at:

    http://ec.europa.eu/idabc/eupl

Unless required by applicable law or agreed to in writing, software
distributed under the Licence is distributed on an 'AS IS' basis,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the Licence for the specific language governing permissions and
limitations under the Licence.
'''

import os
import platform
import re
import signal
import subprocess

from threading import Thread
from tkinter import filedialog
from tkinter import *

APP_NAME = 'OpenADMS Launcher'
APP_VERSION = '1.0'

# Get the name of the operating system, to switch Windows-specific conventions.
OS = platform.system()
# Windows doesn't know the generic "Monospace" name for fixed-width fonts.
MONOSPACE_FONT = 'Courier New' if OS  == 'Windows' else 'Monospace'
# Maximum number of lines in text widget.
CONSOLE_MAX_LINES = 500


class Launcher(Thread):
    """Simple graphical tool to start an HBMQTT message broker and the OpenADMS
    monitoring system."""

    def __init__(self):
        Thread.__init__(self)
        self.start()

    def quit(self):
        self.root.quit()

    def run(self):
        self.root = Tk()
        self.root.resizable(width=False, height=False)
        #self.root.geometry('1000x600')
        self.root.protocol('WM_DELETE_WINDOW', self.quit)
        self.root.title('{} {}'.format(APP_NAME, APP_VERSION))

        self.create_widgets()
        self.align_widgets()

        self.root.mainloop()

    def ask_open_file_name(self):
        """Opens a file dialog window and inserts the path to the selected file
        into the config entry widget."""        
        file_name = filedialog.askopenfilename(
            initialdir='.',
            title='Select Configuration File',
            filetypes = (('JSON Files', '*.json'),
                         ('All Files','*.*'))
        )

        if file_name:
            self.config_entry.delete(0, END)
            self.config_entry.insert(0, file_name)

    def create_widgets(self):
        """Creates all widgets of the user interface."""
        self.frame = Frame(self.root, padx=5, pady=5)
        self.frame.pack(expand=True)
        # Ensure a consistent GUI size.
        #self.frame.grid_propagate(False)
        # Implement stretchability.
        self.frame.grid_rowconfigure(3, weight=1)
        self.frame.grid_columnconfigure(2, weight=1)

        # Textbox for process output.
        self.console = Text(self.frame,
                            borderwidth=3,
                            relief='sunken',
                            height=50,
                            width=160,
                            undo=False)
        # Set read-only.
        self.console.bind('<Key>', lambda e: 'break')
        self.console.configure(background='black',
                               foreground='gold',
                               font=(MONOSPACE_FONT, 10))

        # Scrollbar.
        self.scrollbar = Scrollbar(self.frame, command=self.console.yview)
        self.console['yscrollcommand'] = self.scrollbar.set

        # Path to config file.
        self.config_label = Label(self.frame, text='Configuration File: ')
        self.config_entry = Entry(self.frame,
                                  width=40,
                                  font=(MONOSPACE_FONT, 9))

        if OS == 'Windows':
            # On Microsoft Windows.
            path = 'config\config.json'
        else:
            # On Unix-like operating systems.
            path = './config/config.json'

        self.config_entry.insert(0, path)
        self.config_button = Button(self.frame,
                                    text='...',
                                    command=self.ask_open_file_name)

        # Options.
        self.options_label = Label(self.frame, text='Options:')
        self.debug_var = IntVar()
        self.debug_var.set(1)
        self.debug_check = Checkbutton(self.frame,
                                       text='Show Debug Messages',
                                       variable=self.debug_var)

        # Log Level.
        self.log_level_label = Label(self.frame, text='Log Level:')
        log_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        self.log_level_var = StringVar(self.frame)
        self.log_level_var.set('WARNING')
        self.options = OptionMenu(self.frame, self.log_level_var, *log_levels)

        # Buttons for HBMQTT and OpenADMS.
        self.broker_button = Button(self.frame, width=15)
        self.broker_button['text'] = 'Start\n Message Broker'
        self.broker_button['command'] = self.start_broker

        if OS != 'Windows':
            self.broker_button['state'] = DISABLED

        self.monitoring_button = Button(self.frame, width=15)
        self.monitoring_button['text'] = 'Start\n Monitoring'
        self.monitoring_button['command'] = self.start_monitoring

    def align_widgets(self):
        """Places the widgets in the main window."""
        self.console.grid(column=0, columnspan=4, padx=2, pady=2, row=3,
            sticky='nsew')
        self.scrollbar.grid(column=4, padx=2, pady=2, row=3, sticky='nsew')
        self.config_label.grid(column=0, row=0, sticky='w')
        self.config_entry.grid(column=1, row=0, padx=2, sticky='w')
        self.config_button.grid(column=2, row=0, padx=2, sticky='w')
        self.options_label.grid(column=0, row=2, sticky='w')
        self.debug_check.grid(column=1, row=2, sticky='w')
        self.log_level_label.grid(column=0, row=1, sticky='w')
        self.options.grid(column=1, row=1, sticky='w')
        self.broker_button.grid(column=2, columnspan=1, padx=2, row=0,
            rowspan=2, sticky='ne')
        self.monitoring_button.grid(column=3, columnspan=2, padx=2, row=0,
            rowspan=2, sticky='ne')

    def print_lines(self, pipe, color):
        """Prints the output of a pipe to the console text widget."""
        with pipe:
            for line in pipe:
                # Remove old lines.
                n_lines = int(self.console.index('end-1c').split('.')[0])

                if n_lines > CONSOLE_MAX_LINES:
                    self.console.delete(1.0, 2.0)

                # Remove ANSI colors.
                ansi_escape = re.compile(r'(\x9B|\x1B\[)[0-?]*[ -\/]*[@-~]')
                clean_line = ansi_escape.sub('', line)

                # Set text color of the line.
                self.console.tag_configure(color, foreground=color)
                # Insert text.
                self.console.insert(END, clean_line, color)
                self.console.see(END)

    def kill_process(self, pid):
        """Kills an external process."""
        if OS == 'Windows':
            # On Microsoft Windows.
            os.kill(pid, signal.CTRL_BREAK_EVENT)
        else:
            # On Unix-like operating systems.
            os.killpg(os.getpgid(pid), signal.SIGTERM)

    def start_broker(self):
        """Starts the HBMQTT message broker."""
        self.broker_button['text'] = 'Stop\n Message Broker'
        self.broker_button['command'] = self.stop_broker

        cmd = 'hbmqtt'
        self.broker_process = subprocess.Popen(
            cmd,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
            shell=True,
            stderr=subprocess.STDOUT,
            stdout=subprocess.PIPE,
            universal_newlines=True)

        Thread(target=self.print_lines,
                      args=[self.broker_process.stdout, 'turquoise']).start()

    def stop_broker(self):
        """Stops the message broker."""
        self.broker_button['text'] = 'Start\n Message Broker'
        self.broker_button['command'] = self.start_broker

        self.kill_process(self.broker_process.pid)

    def start_monitoring(self):
        """Reads the options set by the user and starts the OpenADMS
        process."""
        self.monitoring_button['text'] = 'Stop\n Monitoring'
        self.monitoring_button['command'] = self.stop_monitoring

        debug = '--debug' if self.debug_var.get() else ''
        log_level = {
            'CRITICAL': 1,
            'ERROR': 2,
            'WARNING': 3,
            'INFO': 4,
            'DEBUG': 5
        }.get(self.log_level_var.get(), 'WARNING')
        verbosity = '--verbosity {}'.format(log_level)
        config = '--config {}'.format(self.config_entry.get())

        if OS == 'Windows':
            # On Microsoft Windows.
            cmd = 'openadms.py {} {} {}'.format(debug, verbosity, config)
            self.monitoring_process = subprocess.Popen(
                cmd,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
                shell=True,
                stderr=subprocess.STDOUT,
                stdout=subprocess.PIPE,
                universal_newlines=True)
        else:
            # On Unix-like operating systems.
            cmd = 'python3 openadms.py {} {} {}'.format(debug, verbosity, config)
            self.monitoring_process = subprocess.Popen(
                cmd,
                preexec_fn=os.setsid,
                shell=True,
                stderr=subprocess.STDOUT,
                stdout=subprocess.PIPE,
                universal_newlines=True)

        Thread(target=self.print_lines,
               args=[self.monitoring_process.stdout, 'gold']).start()

    def stop_monitoring(self):
        """Stops the monitoring process."""
        self.monitoring_button['text'] = 'Start\n Monitoring'
        self.monitoring_button['command'] = self.start_monitoring

        self.kill_process(self.monitoring_process.pid)

        self.console.insert(END, '[Stopped]')
        self.console.see(END)


if __name__ == '__main__':
    launcher = Launcher()
