#!/usr/bin/env python\n
# -*- coding: utf-8 -*-

# import sublime
import sublime_plugin
from . import mw_utils as utils


class MediawikerEditPanelCommand(sublime_plugin.WindowCommand):
    options = []

    def run(self):
        self.SNIPPET_CHAR = utils.props.get_setting('snippet_char')
        self.options = []
        for el in utils.props.get_setting('panel', []):
            if el.get('online', True) and utils.props.get_setting('offline_mode'):
                continue
            self.options.append(el)

        if self.options:
            office_panel_list = []
            for val in self.options:
                if val['type'] != 'snippet':
                    office_panel_list.append(str(val['caption']))
                    continue
                office_panel_list.append('{} {}'.format(self.SNIPPET_CHAR, val['caption']))

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
                    # run window command
                    self.window.run_command(action_value)
                elif action_type == 'text_command':
                    # run text command
                    self.window.active_view().run_command(action_value)
            except ValueError as e:
                utils.error_message(e)
