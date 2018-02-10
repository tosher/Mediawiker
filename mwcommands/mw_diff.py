#!/usr/bin/env python\n
# -*- coding: utf-8 -*-

import sys

import sublime
import sublime_plugin

import difflib

pythonver = sys.version_info[0]
if pythonver >= 3:
    from . import mw_utils as utils
else:
    import mw_utils as utils


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
            # Uh, well, what if it does exist, but it is empty?
            msg = 'Wiki page %s does not exists.' % (title,)
            utils.status_message(msg)
        else:
            new_lines = view_text.splitlines(True)
            old_lines = text.splitlines(True)
            diff_lines = difflib.unified_diff(old_lines, new_lines, fromfile="Server revision", tofile="Buffer view")
            diff_text = ''.join(diff_lines)
            if not diff_text:
                utils.status_message('Page versions has no differencies')
            else:
                syntax_filename = 'Diff.sublime-syntax' if pythonver >= 3 else 'Diff.tmLanguage'
                syntax = p.from_package(syntax_filename, name='Diff')
                utils.status_message(diff_text, panel_name='Show differences', syntax=syntax, new=True)
