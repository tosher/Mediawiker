#!/usr/bin/env python\n
# -*- coding: utf-8 -*-

import re
import sublime
import sublime_plugin
from . import mw_utils as utils


class MediawikerInsertTemplateCommand(sublime_plugin.WindowCommand):
    ''' alias to Add template command '''

    def run(self):
        self.window.run_command(utils.cmd('page'), {"action": utils.cmd('add_template')})

    def is_visible(self, *args):
        if utils.props.get_setting('offline_mode'):
            return False
        return utils.props.get_view_setting(self.window.active_view(), 'is_here')


class MediawikerAddTemplateCommand(sublime_plugin.TextCommand):

    templates_names = []

    def run(self, edit):
        if utils.props.get_setting('offline_mode'):
            return

        sublime.active_window().show_input_panel('Wiki template prefix:', '', self.show_list, None, None)

    def show_list(self, tpl_prefix):
        self.templates_names = []
        templates = utils.api.call('get_pages', prefix=tpl_prefix, namespace=utils.api.TEMPLATE_NAMESPACE)
        for template in templates:
            self.templates_names.append(utils.api.page_attr(template, 'page_title'))
        sublime.set_timeout(lambda: sublime.active_window().show_quick_panel(self.templates_names, self.on_done), 1)

    def get_template_params(self, text):
        site_active = utils.get_view_site()
        site = utils.props.get_setting('site').get(site_active)
        is_wikia = site.get('is_wikia', False)
        if is_wikia:
            infobox = utils.WikiaInfoboxParser()
            infobox.feed(text)
            params_list = infobox.get_params_list()
            if params_list:
                return ''.join(['|{}\n'.format(p) for p in params_list])

        params_list = []
        pattern = r'(\{{3}.*?\}{3,})'
        parameters = re.findall(pattern, text)
        for param in parameters:
            if param.startswith('{{{'):
                param = param[3:]
            if param.endswith('}}}'):
                param = param[:-3]
            # cut non-param }} from "if" tags, etc..
            # ex: {{#if: ... {{{data2|}}}}}
            close_brackets_diff = param.count('}') - param.count('{')
            if close_brackets_diff > 0:
                param = param[:-close_brackets_diff]
            # default value or not..
            param = param.replace('|', '=') if '|' in param else '{}='.format(param)
            if param not in params_list:
                params_list.append(param)
        return ''.join(['|{}\n'.format(p) for p in params_list])

    def on_done(self, idx):
        if idx >= 0:
            template = utils.api.get_page('Template:{}'.format(self.templates_names[idx]))
            if utils.api.page_can_read(template):
                text = utils.api.page_get_text(page=template)
                params_text = self.get_template_params(text)
                index_of_cursor = self.view.sel()[0].begin()
                # {{ - escapes {
                template_text = '{{{{{0}{1}}}}}'.format(self.templates_names[idx], params_text)
                self.view.run_command(utils.cmd('insert_text'), {'position': index_of_cursor, 'text': template_text})
            # else:
            #     utils.status_message('')
