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


class MediawikerInsertTemplateCommand(sublime_plugin.WindowCommand):
    ''' alias to Add template command '''

    def run(self):
        self.window.run_command("mediawiker_page", {"action": "mediawiker_add_template"})


class MediawikerAddTemplateCommand(sublime_plugin.TextCommand):
    password = ''
    templates_names = []
    sitecon = None

    def run(self, edit, password, title=''):
        self.password = password
        sublime.active_window().show_input_panel('Wiki template prefix:', '', self.show_list, None, None)

    def show_list(self, image_prefix):
        self.templates_names = []
        self.sitecon = mw.get_connect(self.password)
        templates = self.sitecon.allpages(prefix=image_prefix, namespace=mw.TEMPLATE_NAMESPACE)  # images list by prefix
        for template in templates:
            self.templates_names.append(template.page_title)
        sublime.set_timeout(lambda: sublime.active_window().show_quick_panel(self.templates_names, self.on_done), 1)

    def get_template_params(self, text):
        site_active = mw.get_view_site()
        site_list = mw.get_setting('mediawiki_site')
        is_wikia = site_list.get(site_active, {}).get('is_wikia', False)
        if is_wikia:
            infobox = mw.WikiaInfoboxParser()
            infobox.feed(text)
            params_list = infobox.get_params_list()
            if params_list:
                return ''.join(['|%s\n' % p for p in params_list])

        params_list = []
        # ex: {{{title|{{PAGENAME}}}}}
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
            param = param.replace('|', '=') if '|' in param else '%s=' % param
            if param not in params_list:
                params_list.append(param)
        return ''.join(['|%s\n' % p for p in params_list])

    def on_done(self, idx):
        if idx >= 0:
            template = self.sitecon.Pages['Template:%s' % self.templates_names[idx]]
            text = template.text()
            params_text = self.get_template_params(text)
            index_of_cursor = self.view.sel()[0].begin()
            template_text = '{{%s%s}}' % (self.templates_names[idx], params_text)
            self.view.run_command('mediawiker_insert_text', {'position': index_of_cursor, 'text': template_text})
