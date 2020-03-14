#!/usr/bin/env python\n
# -*- coding: utf-8 -*-

import re
import sublime
import sublime_plugin
from . import mw_utils as utils


class MediawikerSearchStringCommand(sublime_plugin.WindowCommand):
    ''' alias to Search string list command '''

    def run(self):
        self.window.run_command(utils.cmd('page'), {"action": utils.cmd('search_string_list')})

    def is_visible(self, *args):
        if utils.props.get_setting('offline_mode'):
            return False
        return True


class MediawikerSearchStringListCommand(sublime_plugin.TextCommand):

    def run(self, edit):
        search_pre = ''
        selection = self.view.sel()
        search_pre = self.view.substr(selection[0]).strip() if selection and len(selection) > 0 else ''
        sublime.active_window().show_input_panel('Wiki search:', search_pre, self.show_results, None, None)

    def do_search(self, string_value):
        nses = utils.get_search_ns()
        if not nses:
            utils.status_message('Search is disabled for {}'.format(utils.get_view_site()))
            return

        namespace = '|'.join(nses)
        search_limit = utils.props.get_setting('search_results_count', 20)
        return utils.api.call('get_search_result', search=string_value, limit=search_limit, namespace=namespace)

    def show_results(self, search_value=''):
        # TODO: paging?
        if search_value:
            search_result = self.do_search(search_value)

        if search_result:

            text = ''
            while True:
                try:
                    hit = search_result.next()
                    if hit:
                        text += self.get_block(hit)
                except StopIteration:
                    break

            if text:
                self.view = sublime.active_window().new_file()
                # TODO: view set attrs in utils..
                syntax_file = utils.props.get_setting('syntax')
                self.view.set_syntax_file(syntax_file)
                self.view.set_name('Wiki search results: {}'.format(search_value))
                self.view.run_command(utils.cmd('insert_text'), {'position': 0, 'text': text})
            elif search_value:
                sublime.message_dialog('No results for: {}'.format(search_value))

    def get_block(self, hit):
        return '* [[{internal}]]\n{data}\n\n'.format(
            internal=hit.get('title', '-'),
            data=self.antispan(hit.get('snippet', '...'))
        )

    def antispan(self, text):
        span_replace_open = "`"
        span_replace_close = "`"
        text = re.sub(r'<span(.*?)>', span_replace_open, text)
        text = re.sub(r'<\/span>', span_replace_close, text)
        # divs cut
        text = re.sub(r'<div(.*?)>', '', text)
        text = re.sub(r'<\/div>', '', text)
        text = text.replace('`', "'''")  # search words highlight
        return text.strip()
