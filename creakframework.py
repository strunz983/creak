#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (c) 2014-2016 Andrea Baldan
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307
# USA

import os
import re
import sys
import imp
import traceback
import subprocess
import shlex
from cmd import Cmd
import creak.utils as utils

N = '\033[m'   # native
R = '\033[31m' # red
G = '\033[32m' # green
O = '\033[33m' # orange
B = '\033[34m' # blue
C = '\033[36m' # cyan
W = '\033[97m' # white
U = '\033[4m'  # underlined
BOLD = '\033[1m'

class Printer(object):

    @staticmethod
    def print_exception(line=''):
        # if self._global_options['debug']:
        # traceback.print_exc()
        line = ' '.join([x for x in [traceback.format_exc().strip().splitlines()[-1], line] if x])
        Printer.error(line)

    @staticmethod
    def error(line):
        '''Formats and presents errors.'''
        if not re.search('[.,;!?]$', line):
            line += '.'
        line = line[:1].upper() + line[1:]
        print('%s%s[!] %s%s' % (U, R, line, N))

    @staticmethod
    def print_output(line):
        '''Formats and presents normal output.'''
        print('%s[*]%s %s' % (C, N, line))

class CreakFramework(Cmd, Printer):

    def __init__(self, args):
        Cmd.__init__(self)
        self.app_path = sys.path[0]
        self._loaded_plugins = {}
        self._loaded_category = {}
        self._plugin_name = args
        self._prompt_template = W + '[%s::%s] > ' + N
        # self.time_format = '%Y-%m-%d %H:%M:%S'
        self.params = {}
        # self._global_options = {'debug': True}
        self.current = None
        self.framework_info = {'author': 'codep', 'version': '1.0'}
        self.base_params = {}

    def _load_plugin(self, dirpath, filename):
        plug_name = filename.split('.')[0]
        plug_dispname = '/'.join(re.split('/plugins/', dirpath)[-1].split('/') + [plug_name])
        plug_loadname = plug_dispname.replace('/', '_')
        plug_loadpath = os.path.join(dirpath, filename)
        plug_file = open(plug_loadpath)
        try:
            # import the module into memory
            imp.load_source(plug_loadname, plug_loadpath, plug_file)
            __import__(plug_loadname)
            # add the module to the framework's loaded modules
            self._loaded_plugins[plug_dispname] = sys.modules[plug_loadname].Plugin(plug_dispname)
            return True
        except ImportError as ex:
            # notify the user of missing dependencies
            self.error('Plugin \'%s\' disabled. Dependency required: \'%s\'' % (plug_dispname, ex))
        except:
            # notify the user of errors
            self.print_exception()
            self.error('Plugin \'%s\' disabled.' % (plug_dispname))

        # remove the module from the framework's loaded modules
        self._loaded_plugins.pop(plug_dispname, None)
        return False

    def _load_plugins(self):
        self._loaded_category = {}
        # crawl the module directory and build the module tree
        for path in [os.path.join(x, 'plugins') for x in (self.app_path, self.app_path)]:
            for dirpath, dirnames, filenames in os.walk(path):
                # remove hidden files and directories
                filenames = [f for f in filenames if not f[0] == '.']
                dirnames[:] = [d for d in dirnames if not d[0] == '.']
                if len(filenames) > 0:
                    for filename in [f for f in filenames if f.endswith('.py')]:
                        is_loaded = self._load_plugin(dirpath, filename)
                        plug_category = 'disabled'
                        if is_loaded:
                            plug_category = re.search('/plugins/([^/]*)', dirpath).group(1)

                        # store the resulting category statistics
                        if not plug_category in self._loaded_category:
                            self._loaded_category[plug_category] = [filename]
                        elif filename not in self._loaded_category[plug_category]:
                            self._loaded_category[plug_category].append(filename)

    def _validate_params(self):
        for param in self.current.required_params:
            if self.current.required_params[param] is True and param not in self.params and param in self.base_params:
                self.params[param] = self.base_params[param]
            elif self.current.required_params[param] is True and param not in self.params:
                print('Value required for mandatory \'%s\' parameter.' % (param.upper()))
                return False
        return True

    def init_framework(self):
        """
        Init the framework, loading all plugins and setting all class variables,
        trying also to retrieve some basic info from the system
        """
        self._load_plugins()
        self.prompt = self._prompt_template % ('creak', 'base')
        print('')
        self.print_output('Loaded %s plugins ' % len(self._loaded_plugins))
        self.print_output('Categories:\n')
        for category in sorted(self._loaded_category):
            if category != 'disabled':
                self.print_output('{}{}({}){}'.format(G, category, len(self._loaded_category[category]), N))
            else:
                self.print_output('{}{}({}){}'.format(R, category, len(self._loaded_category[category]), N))
            for plugin in self._loaded_category[category]:
                if category != 'disabled':
                    print('     + {}{}{}'.format(G, plugin, N))
                else:
                    print('     + {}{}{}'.format(R, plugin, N))
            print('')
        strs = subprocess.check_output(shlex.split('ip r l'))
        gateway = strs.split('default via')[-1].split()[0]
        dev = strs.split('dev')[-1].split()[0]
        localip = strs.split('src')[-1].split()[0]
        mac_addr = utils.get_mac_by_dev(dev)
        self.base_params['dev'], self.base_params['gateway'], self.base_params['localip'] = dev, gateway, localip
        if mac_addr:
            self.base_params['mac_addr'] = mac_addr
        print('')
        self.print_output('Detected some informations\n')
        for param in sorted(self.base_params):
            print(' {}{:.<12}{}{:.>15}{}{}'.format(BOLD, param, N, W, self.base_params[param], N))
        return True

    def emptyline(self):
        pass

    def default(self, line):
        self.do_shell(line)

    def parseline(self, line):
        if '|' in line:
            return 'pipe', line.split('|'), line
        return Cmd.parseline(self, line)

    def do_shell(self, line):
        "Run a shell command"
        output = os.popen(line).read()
        if line == 'ls':
            files = output.split('\n')
            for f in files:
                if os.path.isdir(f):
                    print('{}{}{}{}'.format(BOLD, B, f, N))
                else:
                    print(f)
        else:
            print('\n%s' % output)

    def do_pipe(self, args):
        buffer = None
        for arg in args:
            s = arg
            if buffer:
                # This command just adds the output of a previous command as the last argument
                s += ' ' + buffer

            # self.onecmd(s)
            # buffer = self.output

    def do_load(self, args):
        '''Loads specified module'''
        self.params = {}
        if not args:
            return
        # finds any plugins that contain args
        plugins = [args] if args in self._loaded_plugins else [x for x in self._loaded_plugins if args in x]
        # notify the user if none or multiple plugins are found
        if len(plugins) != 1:
            if not plugins:
                self.error('Invalid module name.')
            else:
                self.print_output('Multiple plugins match \'%s\'.' % args)
            return
        # load the module
        plug_dispname = plugins[0]
        # loop to support reload logic
        plugin = self._loaded_plugins[plug_dispname]
        plugin.init_plugin()
        self.current = plugin
        # self.required_params = plugin.required_params
        self.prompt = self._prompt_template % (self.prompt[6:11], plug_dispname.split('/')[-1])

    def do_set(self, args):
        '''Sets module options'''
        params = args.split()
        name = params[0].lower()
        if name in self.current.required_params:
            value = ' '.join(params[1:])
            self.params[name] = value
            print('%s => %s' % (name.upper(), value))
        else:
            self.error('Invalid parameter.')

    def do_unset(self, args):
        '''Unsets module params'''
        self.do_set('%s %s' % (args, 'None'))

    def do_run(self, args):
        '''Runs the module'''
        try:
            self._summary_counts = {}
            is_valid = self._validate_params()
            if is_valid:
                if self.current.root and os.geteuid() != 0:
                    self.error('Root permissions required')
                    return
                self.current.run(self.params)
            else:
                return
        except KeyboardInterrupt:
            print('')
        except Exception:
            self.print_exception()

    def do_showinfo(self, args):
        if self.current:
            self.current.print_info()
        else:
            for field in sorted(self.framework_info):
                print('{}: {}'.format(field, self.framework_info[field]))

    def do_clean(self, args):
        '''Exits the current context'''
        self.params = {}
        self.current = None

    def do_quit(self, args):
        print('Quitting..')
        raise SystemExit

    do_exit = do_quit
    do_q = do_quit

if __name__ == '__main__':
    prompt = CreakFramework('CreakShell')
    prompt.init_framework()
    prompt.cmdloop('\nStarting prompt...\n')
