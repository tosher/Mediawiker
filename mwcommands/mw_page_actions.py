#!/usr/bin/env python\n
# -*- coding: utf-8 -*-

# import sublime
import sublime_plugin
from . import mw_utils as utils


class MediawikerPageCommand(sublime_plugin.WindowCommand):
    '''prepare all actions with wiki'''

    def run(self, action, action_params=None, **kwargs):
        self.action = action
        self.action_params = action_params

        if not utils.conman.require_password():
            panel_passwd = utils.InputPanelPassword(callback=self.command_run)
            panel_passwd.get_password()
        else:
            utils.set_timeout_async(self.command_run, 0)

    def command_run(self):
        self.window.active_view().run_command(self.action, self.action_params)

    def is_visible(self, *args):
        return False
