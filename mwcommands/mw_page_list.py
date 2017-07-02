#!/usr/bin/env python\n
# -*- coding: utf-8 -*-

import sys

import sublime
import sublime_plugin

pythonver = sys.version_info[0]
if pythonver >= 3:
    from . import mw_utils as utils
else:
    import mw_utils as utils


class MediawikerPageListCommand(sublime_plugin.WindowCommand):

    def run(self, storage_name='pagelist'):
        site_name_active = utils.get_view_site()
        pagelist = utils.props.get_setting(storage_name, {})
        self.my_pages = pagelist.get(site_name_active, [])
        if self.my_pages:
            self.my_pages.reverse()
            sublime.set_timeout(lambda: self.window.show_quick_panel(self.my_pages, self.on_done), 1)
        else:
            utils.status_message('List of pages for wiki "%s" is empty.' % (site_name_active))

    def on_done(self, index):
        if index >= 0:
            title = self.my_pages[index]
            try:
                self.window.run_command(utils.cmd('page'), {
                    'action': utils.cmd('show_page'),
                    'action_params': {'title': title}
                })
            except ValueError as e:
                sublime.message_dialog(e)
