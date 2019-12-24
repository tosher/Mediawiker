#!/usr/bin/env python\n
# -*- coding: utf-8 -*-

import sublime
import sublime_plugin
import difflib
from . import mw_utils as utils


class MediawikerShowDiffCommand(sublime_plugin.WindowCommand):
    ''' alias to MediawikerPageDiffVsServerCommand '''

    def run(self):
        self.window.run_command(utils.cmd('page'), {"action": utils.cmd('page_diff_vs_server')})

    def is_visible(self, *args):
        if utils.props.get_setting('offline_mode'):
            return False
        return utils.props.get_view_setting(self.window.active_view(), 'is_here')


class MediawikerPageDiffVsServerCommand(sublime_plugin.TextCommand):
    '''
    Page diff vs server revision
    Based on scholer's fork command:
    * https://github.com/scholer/Mediawiker/
    * https://github.com/scholer/Mediawiker/blob/master/mediawiker.py#L595
    '''

    def run(self, edit):
        if utils.props.get_setting('offline_mode'):
            return

        title = utils.get_title()
        view_text = self.view.substr(sublime.Region(0, self.view.size()))

        page = utils.api.call('get_page', title=title)
        text = utils.api.page_get_text(page)

        if not text:
            utils.error_message('Wiki page "{}" does not exists.'.format(title))
        else:
            new_lines = view_text.splitlines(True)
            old_lines = text.splitlines(True)
            diff_lines = difflib.unified_diff(old_lines, new_lines, fromfile="Server revision", tofile="Buffer view")
            diff_text = ''.join(diff_lines)
            if not diff_text:
                utils.status_message('Page versions has no differencies', is_panel=True)
            else:
                syntax_filename = 'Diff.sublime-syntax'
                syntax = utils.p.from_package(syntax_filename, name='Diff')
                utils.status_message(diff_text, is_panel=True, panel_name='Show differences', syntax=syntax, new=True)
