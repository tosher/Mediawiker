#!/usr/bin/env python\n
# -*- coding: utf-8 -*-

import sys

# import sublime
import sublime_plugin

pythonver = sys.version_info[0]
if pythonver >= 3:
    from . import mw_utils as mw
else:
    import mw_utils as mw


class MediawikerPageCommand(sublime_plugin.WindowCommand):
    '''prepare all actions with wiki'''

    def run(self, action, action_params=None, **kwargs):
        self.action = action
        self.action_params = action_params

        if not mw.conman.require_password():
            panel_passwd = mw.InputPanelPassword(callback=self.command_run)
            panel_passwd.get_password()
        else:
            mw.set_timeout_async(self.command_run, 0)

    def command_run(self):
        self.window.active_view().run_command(self.action, self.action_params)
