#!/usr/bin/env python\n
# -*- coding: utf-8 -*-

import sublime
import sublime_plugin
from . import mw_utils as utils


class MediawikerPageListCommand(sublime_plugin.WindowCommand):

    def run(self, storage_name='pagelist'):
        self.storage_name = storage_name
        site_name_active = utils.get_view_site()
        self.pagelist = utils.props.get_setting(storage_name, {})
        self.my_pages = self.get_pages(site_name_active)

        # show pages from the sites with the same host
        show_extended = utils.props.get_setting('show_favorites_and_history_by_site_host')
        if show_extended:
            sites = utils.props.get_setting('site')
            host = utils.props.get_site_setting(site_name_active, 'host')

            for site in sites.keys():
                if site == site_name_active:
                    continue
                h = utils.props.get_site_setting(site, 'host')
                if host == h:
                    h_pages = self.get_pages(site)
                    self.my_pages = list(set().union(self.my_pages, h_pages))

        if self.my_pages:
            self.my_pages.reverse()
            sublime.set_timeout(lambda: self.window.show_quick_panel(self.my_pages, self.on_done), 1)
        else:
            utils.error_message('List of pages for wiki "{}" is empty.'.format(site_name_active))

    def get_pages(self, site_name):
        return self.pagelist.get(site_name, [])

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
