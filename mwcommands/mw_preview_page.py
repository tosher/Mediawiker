#!/usr/bin/env python\n
# -*- coding: utf-8 -*-

import sys
import os
import re
import webbrowser
import tempfile
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
        self.window.run_command("mediawiker_page", {"action": "mediawiker_preview_page"})


class MediawikerPreviewPageCommand(sublime_plugin.TextCommand):
    '''
    Very restricted HTML Preview
    NOTE: Beta
    '''

    def run(self, edit, title, password):
        sitecon = mw.get_connect(password)
        text = self.view.substr(sublime.Region(0, self.view.size()))

        site_active = mw.get_view_site()
        site_list = mw.get_setting('mediawiki_site')
        host = site_list[site_active]['host']
        path = site_list[site_active]['path']
        head_default = mw.get_setting('mediawiki_preview_head')
        head = '\n'.join(site_list[site_active].get('preview_custom_head', head_default))
        lang = mw.get_setting('mediawiki_preview_lang', 'en')
        preview_file = mw.get_setting('mediawiki_preview_file', 'Wiki_page_preview_')
        site_http = 'https' if site_list[site_active].get('https', False) else 'http'

        html_header_lines = [
            '<!DOCTYPE html>',
            '<html>',
            '<head>',
            '%(head)s',
            '</head>',
            '<body style="margin:20px;">'
        ]

        geshi_css = self.get_geshi_langs()
        head_tpl = Template(head)
        head_str = head_tpl.render(http=site_http, host=host, path=path, lang=lang, geshi_css=geshi_css)
        html_header = '\n'.join(html_header_lines) % {'head': head_str}
        html_footer = '</body></html>'

        html = sitecon.parse(text=text, title=mw.get_title(), disableeditsection=True).get('text', {}).get('*', '')
        html = html.replace('"//', '"%s://' % site_http)  # internal links: images,..
        html = html.replace('"/', '"%s://%s/' % (site_http, host))  # internal local links: images,..

        if preview_file.endswith('.html'):
            preview_file = os.path.join(sublime.packages_path(), 'User', preview_file)
            # fixed file in User folder
            if pythonver >= 3:
                with open(preview_file, 'w', encoding='utf-8') as tf:
                    tf.write(html_header)
                    tf.write(html)
                    tf.write(html_footer)
            else:
                with open(preview_file, 'w') as tf:
                    tf.write(html_header)
                    tf.write(html.encode('utf-8'))
                    tf.write(html_footer)
            html_view = sublime.active_window().find_open_file(preview_file)
            if html_view:
                sublime.active_window().focus_view(html_view)
            else:
                sublime.active_window().open_file(preview_file)
                webbrowser.open(tf.name)
        else:
            # temporary file
            if pythonver >= 3:
                with tempfile.NamedTemporaryFile(mode='w+t', suffix='.html', prefix=preview_file, dir=None, delete=False, encoding='utf-8') as tf:
                    tf.write(html_header)
                    tf.write(html)
                    tf.write(html_footer)
            else:
                with tempfile.NamedTemporaryFile(mode='w+t', suffix='.html', prefix=preview_file, dir=None, delete=False) as tf:
                    tf.write(html_header)
                    tf.write(html.encode('utf-8'))
                    tf.write(html_footer)
            webbrowser.open(tf.name)

    def get_geshi_langs(self):
        langs = []
        pattern = r'<(source|syntaxhighlight) lang="(.*?)"(.*?)>'
        self.regions = self.view.find_all(pattern)
        for r in self.regions:
            lang = re.sub(pattern, r'\2', self.view.substr(r))
            langs.append(lang)
        return 'ext.geshi.language.%s|' % ','.join(set(langs)) if langs else ''
