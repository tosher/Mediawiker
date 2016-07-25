#!/usr/bin/env python\n
# -*- coding: utf-8 -*-

import sys

import sublime
import sublime_plugin

pythonver = sys.version_info[0]
if pythonver >= 3:
    from . import mw_utils as mw
else:
    import mw_utils as mw


class MediawikerEditPanelCommand(sublime_plugin.WindowCommand):
    options = []
    SNIPPET_CHAR = u'\u24C8'

    def run(self):
        self.SNIPPET_CHAR = mw.get_setting('mediawiker_snippet_char')
        self.options = mw.get_setting('mediawiker_panel', {})
        if self.options:
            office_panel_list = ['\t%s' % val['caption'] if val['type'] != 'snippet' else '\t%s %s' % (self.SNIPPET_CHAR, val['caption']) for val in self.options]
            self.window.show_quick_panel(office_panel_list, self.on_done)

    def on_done(self, index):
        if index >= 0:
            # escape from quick panel return -1
            try:
                action_type = self.options[index]['type']
                action_value = self.options[index]['value']
                if action_type == 'snippet':
                    # run snippet
                    self.window.active_view().run_command("insert_snippet", {"name": action_value})
                elif action_type == 'window_command':
                    # run command
                    self.window.run_command(action_value)
                elif action_type == 'text_command':
                    # run command
                    self.window.active_view().run_command(action_value)
            except ValueError as e:
                sublime.status_message(e)
