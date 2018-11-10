#!/usr/bin/env python\n
# -*- coding: utf-8 -*-

import webbrowser
import sublime
import sublime_plugin
from . import mw_utils as utils


class MediawikerPreviewSandboxCommand(sublime_plugin.WindowCommand):
    ''' alias to Preview page command '''

    def run(self):
        self.window.run_command(utils.cmd('page'), {"action": utils.cmd('preview_page_sandbox')})

    def is_visible(self, *args):
        if utils.props.get_setting('offline_mode'):
            return False
        return utils.props.get_view_setting(self.window.active_view(), 'is_here')


class MediawikerPreviewPageSandboxCommand(sublime_plugin.TextCommand):
    '''
    Page preview with existed sandox page
    '''

    def run(self, edit):
        if utils.props.get_setting('offline_mode'):
            return

        utils.props.set_view_setting(self.view, 'preview_cmd', 'preview_sandbox')

        title = utils.get_title()
        text = self.view.substr(sublime.Region(0, self.view.size()))
        text = '{{{{DISPLAYTITLE:{}}}}}\n\n{}'.format(title, text)  # replace sandbox page title with editable page title
        page_sandbox_name = utils.props.get_site_setting(utils.get_view_site(), 'preview_sandbox')

        if not page_sandbox_name:
            utils.status_message('Sandbox preview page for site %s is not defined in the settings (option "preview_sandbox").' % (utils.get_view_site()))
            return

        page_sandbox_url = utils.get_page_url(page_sandbox_name)
        page_sandbox = utils.api.get_page(page_sandbox_name)

        is_success = utils.api.save_page(
            page=page_sandbox,
            text=text,
            summary='Preview for page {}'.format(title),
            mark_as_minor=True
        )
        if not is_success:
            utils.status_message('There was an error while trying to post page [[%s]] to sandbox page %s. Site: "%s".' % (title, page_sandbox_name, utils.get_view_site()), replace=['[', ']'])
            return

        if utils.props.get_view_setting(self.view, 'autoreload') == 0:
            webbrowser.open(page_sandbox_url)
