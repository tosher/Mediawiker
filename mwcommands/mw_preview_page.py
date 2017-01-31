#!/usr/bin/env python\n
# -*- coding: utf-8 -*-

import sys
import os
import re
import webbrowser
from jinja2 import Template

import sublime
import sublime_plugin

pythonver = sys.version_info[0]
if pythonver >= 3:
    from . import mw_utils as mw
else:
    import mw_utils as mw


class MediawikerPreviewCommand(sublime_plugin.WindowCommand):
    ''' alias to Preview page command '''

    def run(self):
        self.window.run_command(mw.cmd('page'), {"action": mw.cmd('preview_page')})


class MediawikerPreviewPageCommand(sublime_plugin.TextCommand):
    '''
    Very restricted HTML Preview
    '''

    def run(self, edit):
        text = self.view.substr(sublime.Region(0, self.view.size()))
        # site = mw.get_setting('site').get(mw.get_view_site())
        site = mw.conman.get_site()

        page_css = mw.api.call('get_page', title='MediaWiki:Common.css')
        text_css = mw.api.page_get_text(page_css)
        if text_css:
            common_css = '''
            <style type="text/css">
            %s
            </style>
            ''' % text_css
        else:
            common_css = ''

        host = site['host']
        path = site['path']
        head = '\n'.join(site['preview_custom_head'] or mw.get_setting('preview_head'))
        lang = mw.get_setting('preview_lang')
        self.page_id = '%s: %s' % (host, mw.get_title())
        self.preview_file = mw.from_package('%s_preview_file.html' % mw.PML, name='User', posix=False, is_abs=True)
        site_http = 'https' if site['https'] else 'http'

        html_header_lines = [
            '<!DOCTYPE html>',
            '<html>',
            '<head>',
            '%(head)s',
            '%(common_css)s'
            '</head>',
            '<body style="margin:20px;">'
        ]

        geshi_css = self.get_geshi_langs()
        head_tpl = Template(head)
        head_str = head_tpl.render(http=site_http, host=host, path=path, lang=lang, geshi_css=geshi_css)
        html_header = '\n'.join(html_header_lines) % {'head': head_str, 'common_css': common_css}
        html_footer = '</body></html>'

        html = mw.api.call('get_parse_result', text=text, title=mw.get_title())
        html = html.replace('"//', '"%s://' % site_http)  # internal links: images,..
        html = html.replace('"/', '"%s://%s/' % (site_http, host))  # internal local links: images,..

        page_id_old = self.get_page_id()
        page = self.generate_preview(html_header, html, html_footer)
        if self.page_id != page_id_old or mw.props.get_view_setting(self.view, 'autoreload') == 0:
            webbrowser.open(page)

    def get_page_id(self):
        if not os.path.exists(self.preview_file):
            return None
        with open(self.preview_file, 'r') as tf:
            first_line = tf.readline()
        return first_line.replace('<!--', '').replace('-->', '').replace('\n', '')

    def generate_preview(self, header, data, footer):
        if pythonver >= 3:
            with open(self.preview_file, 'w', encoding='utf-8') as tf:
                tf.write('<!--%s-->\n' % self.page_id)
                tf.write(header)
                tf.write(data)
                tf.write(footer)
        else:
            with open(self.preview_file, 'w') as tf:
                tf.write('<!--%s-->\n' % self.page_id)
                tf.write(header.encode('utf-8'))
                tf.write(data.encode('utf-8'))
                tf.write(footer.encode('utf-8'))
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
        return 'ext.geshi.language.%s|' % ','.join(set(langs)) if langs else ''
