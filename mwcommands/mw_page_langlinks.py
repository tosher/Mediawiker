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


class MediawikerShowPageLanglinksCommand(sublime_plugin.WindowCommand):
    ''' alias to Get page command '''

    def run(self):
        self.window.run_command("mediawiker_page", {"action": "mediawiker_page_langlinks"})


class MediawikerPageLanglinksCommand(sublime_plugin.TextCommand):

    def run(self, edit, title, password):
        sitecon = mw.get_connect(password)
        # selection = self.view.sel()
        # search_pre = self.view.substr(selection[0]).strip()
        selected_text = self.view.substr(self.view.sel()[0]).strip()
        title = selected_text if selected_text else title
        self.mw_get_page_langlinks(sitecon, title)

        self.lang_prefixes = []
        for lang_prefix in self.links.keys():
            self.lang_prefixes.append(lang_prefix)

        self.links_names = ['%s: %s' % (lp, self.links[lp]) for lp in self.lang_prefixes]
        if self.links_names:
            sublime.active_window().show_quick_panel(self.links_names, self.on_done)
        else:
            sublime.status_message('Unable to find laguage links for "%s"' % title)

    def mw_get_page_langlinks(self, site, title):
        self.links = {}
        page = site.Pages[title]
        linksgen = page.langlinks()
        if linksgen:
            while True:
                try:
                    prop = linksgen.next()
                    self.links[prop[0]] = prop[1]
                except StopIteration:
                    break

    def on_done(self, index):
        if index >= 0:
            self.lang_prefix = self.lang_prefixes[index]
            self.page_name = self.links[self.lang_prefix]

            self.process_options = ['Open selected page', 'Replace selected text']
            sublime.active_window().show_quick_panel(self.process_options, self.process)

    def process(self, index):
        if index == 0:
            site_active_new = None
            site_active = mw.get_view_site()
            sites = mw.get_setting('mediawiki_site')
            host = sites[site_active]['host']
            domain_first = '.'.join(host.split('.')[-2:])
            # NOTE: only links like lang_prefix.site.com supported.. (like en.wikipedia.org)
            host_new = '%s.%s' % (self.lang_prefix, domain_first)
            # if host_new exists in settings we can open page
            for site in sites:
                if sites[site]['host'] == host_new:
                    site_active_new = site
                    break
            if site_active_new:
                # open page with force site_active_new
                sublime.active_window().run_command("mediawiker_page", {"title": self.page_name, "action": "mediawiker_show_page", "site_active": site_active_new})
            else:
                sublime.status_message('Settings not found for host %s.' % (host_new))
        elif index == 1:
            self.view.run_command('mediawiker_replace_text', {'text': self.page_name})
