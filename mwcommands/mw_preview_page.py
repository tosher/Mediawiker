#!/usr/bin/env python\n
# -*- coding: utf-8 -*-

import os
import re
import webbrowser
from jinja2 import Template
import sublime
import sublime_plugin
from . import mw_utils as utils


class MediawikerPreviewCommand(sublime_plugin.WindowCommand):
    ''' alias to Preview page command '''

    def run(self):
        self.window.run_command(utils.cmd('page'), {"action": utils.cmd('preview_page')})

    def is_visible(self, *args):
        if utils.props.get_setting('offline_mode'):
            return False
        return utils.props.get_view_setting(self.window.active_view(), 'is_here')


class MediawikerPreviewPageCommand(sublime_plugin.TextCommand):
    '''
    Very restricted HTML Preview
    '''

    def template_args(self, site):
        return {
            'http': 'https' if site['https'] else 'http',
            'host': site['host'],
            'path': site['path'],
            'lang': utils.props.get_setting('preview_lang'),
            'geshi_css': self.get_geshi_langs(),
            'title': utils.get_title()
        }

    def run(self, edit):
        if utils.props.get_setting('offline_mode'):
            return

        utils.props.set_view_setting(self.view, 'preview_cmd', 'preview')

        text = self.view.substr(sublime.Region(0, self.view.size()))
        site = utils.conman.get_site()

        page_css = utils.api.call('get_page', title='MediaWiki:Common.css')
        text_css = utils.api.page_get_text(page_css)
        if text_css:
            common_css = '''
            <style type="text/css">
            {}
            </style>
            '''.format(text_css)
        else:
            common_css = ''

        head_tpl_args = self.template_args(site)
        self.page_id = '{}: {}'.format(head_tpl_args['host'], utils.get_title())
        self.preview_file = utils.p.from_package('{}_preview_file.html'.format(utils.p.PML), name='User', posix=False, is_abs=True)

        html_header_lines = [
            '<!DOCTYPE html>',
            '<html>',
            '<head>',
            '{head}',
            '{common_css}'
            '</head>',
            '<body style="margin:20px;">'
        ]

        head = '\n'.join(site['preview_custom_head'] or utils.props.get_setting('preview_head'))
        head_tpl = Template(head)
        head_str = head_tpl.render(**head_tpl_args)
        html_header = '\n'.join(html_header_lines).format(head=head_str, common_css=common_css)
        html_footer = '</body></html>'

        html = utils.api.call('get_parse_result', text=text, title=utils.get_title())
        html = html.replace('"//', '"{}://'.format(head_tpl_args['http']))  # internal links: images,..
        html = html.replace('"/', '"{}://{}/'.format(head_tpl_args['http'], head_tpl_args['host']))  # internal local links: images,..

        page_id_old = self.get_page_id()
        page = self.generate_preview(html_header, html, html_footer)
        if self.page_id != page_id_old or utils.props.get_view_setting(self.view, 'autoreload') == 0:
            webbrowser.open('file:///{}'.format(page))

    def get_page_id(self):
        if not os.path.exists(self.preview_file):
            return None
        with open(self.preview_file, 'r', encoding='utf-8') as tf:
            first_line = tf.readline()
        return first_line.replace('<!--', '').replace('-->', '').replace('\n', '')

    def generate_preview(self, header, data, footer):
        with open(self.preview_file, 'w', encoding='utf-8') as tf:
            tf.write('<!--{}-->\n'.format(self.page_id))
            tf.write(header)
            tf.write(data)
            tf.write(footer)
        return tf.name

    def get_geshi_langs(self):
        # NOTE: in last mediawiki versions module "pygments" is using, not need to generate langs list
        # just use css string with pygments and remove geshi string
        langs = []
        pattern = r'<(source|syntaxhighlight) lang="(.*?)"(.*?)>'
        self.regions = self.view.find_all(pattern)
        for r in self.regions:
            lang = re.sub(pattern, r'\2', self.view.substr(r))
            langs.append(lang)
        return 'ext.geshi.language.{}|'.format(','.join(set(langs)) if langs else '')
