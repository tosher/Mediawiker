#!/usr/bin/env python\n
# -*- coding: utf-8 -*-

import sys
import re

import sublime
import sublime_plugin

pythonver = sys.version_info[0]
if pythonver >= 3:
    from . import mw_utils as mw
else:
    import mw_utils as mw


class MediawikerSearchStringCommand(sublime_plugin.WindowCommand):
    ''' alias to Search string list command '''

    def run(self):
        self.window.run_command("mediawiker_page", {"action": "mediawiker_search_string_list"})


class MediawikerSearchStringListCommand(sublime_plugin.TextCommand):
    password = ''
    title = ''
    search_limit = 20
    pages_names = []
    search_result = None

    def run(self, edit, title, password):
        self.password = password
        search_pre = ''
        selection = self.view.sel()
        search_pre = self.view.substr(selection[0]).strip() if selection else ''
        sublime.active_window().show_input_panel('Wiki search:', search_pre, self.show_results, None, None)

    def show_results(self, search_value=''):
        # TODO: paging?
        self.pages_names = []
        self.search_limit = mw.get_setting('mediawiker_search_results_count')
        if search_value:
            self.search_result = self.do_search(search_value)
        if self.search_result:
            for i in range(self.search_limit):
                try:
                    page_data = self.search_result.next()
                    self.pages_names.append([page_data['title'], page_data['snippet']])
                except:
                    pass
            te = ''
            search_number = 1
            for pa in self.pages_names:
                te += '### %s. %s\n* [%s](%s)\n\n%s\n\n' % (search_number, pa[0], pa[0], mw.get_page_url(pa[0]), self.antispan(pa[1]))
                search_number += 1

            if te:
                self.view = sublime.active_window().new_file()
                syntax_file = mw.get_setting('mediawiki_search_syntax', 'Packages/Markdown/Markdown.tmLanguage')
                self.view.set_syntax_file(syntax_file)
                self.view.set_name('Wiki search results: %s' % search_value)
                self.view.run_command('mediawiker_insert_text', {'position': 0, 'text': te})
            elif search_value:
                sublime.message_dialog('No results for: %s' % search_value)

    def antispan(self, text):
        span_replace_open = "`"
        span_replace_close = "`"
        # bold and italic tags cut
        text = text.replace("'''", "")
        text = text.replace("''", "")
        # spans to bold
        text = re.sub(r'<span(.*?)>', span_replace_open, text)
        text = re.sub(r'<\/span>', span_replace_close, text)
        # divs cut
        text = re.sub(r'<div(.*?)>', '', text)
        text = re.sub(r'<\/div>', '', text)
        text = text.replace('`', '**')  # search words highlight
        return text

    def do_search(self, string_value):
        sitecon = mw.get_connect(self.password)
        namespace = mw.get_setting('mediawiker_search_namespaces')
        return sitecon.search(search=string_value, what='text', limit=self.search_limit, namespace=namespace)
