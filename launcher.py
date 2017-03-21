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
import shlex
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

class App(Thread):

    def __init__(self):
        Thread.__init__(self)
        self.start()

    def callback(self):
        self.root.quit()

    def run(self):
        self.root = Tk()
        self.root.resizable(width=False, height=False)
        #self.root.geometry('1000x600')
        self.root.protocol('WM_DELETE_WINDOW', self.callback)
        self.root.title('{} {}'.format(APP_NAME, APP_VERSION))

        self.create_widgets()

        self.root.mainloop()

    def ask_open_file_name(self):
        file_name = filedialog.askopenfilename(
            initialdir='.',
            title='Select Configuration File',
            filetypes = (('JSON Files', '*.json'),
                         ('All Files','*.*'))
        )

        if file_name:
            self.e.delete(0, END)
            self.e.insert(0, file_name)

    def create_widgets(self):
        self.frame = Frame(self.root, padx=5, pady=5)
        self.frame.pack(expand=True)
        # ensure a consistent GUI size
        #self.frame.grid_propagate(False)
        # implement stretchability
        self.frame.grid_rowconfigure(3, weight=1)
        self.frame.grid_columnconfigure(2, weight=1)

        #
        # Textbox
        #
        self.text = Text(self.frame,
                         borderwidth=5,
                         relief='sunken',
                         height=50,
                         width=160)
        self.text.configure(background='black',
                            foreground='gold',
                            font=(MONOSPACE_FONT, 10))

        #
        # Scrollbar
        #
        self.scrollbar = Scrollbar(self.frame, command=self.text.yview)
        self.text['yscrollcommand'] = self.scrollbar.set

        # Config Entry
        l1 = Label(self.frame, text='Configuration File: ')

        self.e = Entry(self.frame, width=40, font=(MONOSPACE_FONT, 10))
        self.e.insert(0, './config/config.json')

        b = Button(self.frame, text='...', command=self.ask_open_file_name)

        #
        # Debug Messages
        #
        l2 = Label(self.frame, text='Options:')
        self.var = IntVar()
        self.var.set(1)
        self.check = Checkbutton(self.frame,
                                 text='Show Debug Messages',
                                 variable=self.var)

        #
        # Log Level
        #
        l3 = Label(self.frame, text='Log Level:')

        choices = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        choice_var = StringVar(self.frame)
        choice_var.set('WARNING')

        self.options = OptionMenu(self.frame, choice_var, *choices)

        #
        # Start/Stop Button
        #
        self.button = Button(self.frame)
        self.button['text'] = 'Start\n Monitoring'
        self.button['command'] = self.start_monitoring

        self.text.grid(row=3, column=0, columnspan=4, sticky='nsew', padx=2, pady=2)
        self.scrollbar.grid(row=3, column=4, sticky='nsew', padx=2, pady=2)
        l1.grid(row=0, column=0, sticky='w')
        self.e.grid(row=0, column=1, sticky='w')
        b.grid(row=0, column=2, sticky='w')
        l2.grid(row=2, column=0, sticky='w')
        self.check.grid(row=2, column=1, sticky='w')
        l3.grid(row=1, column=0, sticky='w')
        self.options.grid(row=1, column=1, sticky='w')
        self.button.grid(row=0, column=3, rowspan=3, columnspan=2, sticky='ne')

        # self.quit = Button(self, text='QUIT', fg='red',
        #                       command=root.destroy)
        # self.quit.pack(side='bottom')

    def print_lines(self, pipe):
        with pipe:
            for line in pipe:
                ansi_escape = re.compile(r'(\x9B|\x1B\[)[0-?]*[ -\/]*[@-~]')
                clean = ansi_escape.sub('', str(line))
                self.text.insert(END, clean)
                self.text.see(END)

    def stop_monitoring(self):
        self.button['text'] = 'Start\n Monitoring'
        self.button['command'] = self.stop_monitoring

        if OS == 'Windows':
            os.kill(self.process.pid, signal.CTRL_BREAK_EVENT)
        else:
            os.killpg(os.getpgid(self.process.pid), signal.SIGTERM)

        self.text.insert(END, '[Stopped]')
        self.text.see(END)

    def start_monitoring(self):
        self.button['text'] = 'Stop\n Monitoring'
        self.button['command'] = self.stop_monitoring

        cmd = 'openadms.py --debug --verbosity 3 --config config/example.json'

        if OS == 'Windows':
            self.process = subprocess.Popen(
                cmd,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
                shell=True,
                stderr=subprocess.STDOUT,
                stdout=subprocess.PIPE,
                universal_newlines=True)
        else:
            self.process = subprocess.Popen(
                cmd,
                preexec_fn=os.setsid,
                shell=True,
                stderr=subprocess.STDOUT,
                stdout=subprocess.PIPE,
                universal_newlines=True)

        Thread(target=self.print_lines, args=[self.process.stdout]).start()


if __name__ == '__main__':
    app = App()
