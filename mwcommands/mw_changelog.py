#!/usr/bin/env python\n
# -*- coding: utf-8 -*-

import re
import webbrowser
import sublime
import sublime_plugin
from . import mw_utils as utils
from . import mw_html


class MediawikerChangelogCommand(sublime_plugin.TextCommand):

    DRAW_TYPE = sublime.HIDDEN + sublime.PERSISTENT

    def run(self, edit, version='sublime'):
        self.MARKED = utils.props.get_setting('config_icon_checked')
        self.UNMARKED = utils.props.get_setting('config_icon_unchecked')
        self.RADIO_MARKED = utils.props.get_setting('config_icon_radio_checked')
        self.RADIO_UNMARKED = utils.props.get_setting('config_icon_radio_unchecked')
        self.EDIT_ICON = utils.props.get_setting('config_icon_edit')
        self.BACK_ICON = utils.props.get_setting('config_icon_back')
        self.LIST_ICON = utils.props.get_setting('config_icon_unnumbered_list')

        self.html = mw_html.MwHtmlAdv(html_id='mediawiker_changelog', user_css=False)
        self.set_css()
        # self.html.debug = True

        with open(utils.p.from_package('Changelog.mediawiki', posix=False, is_abs=True), 'r', encoding='utf-8') as cl:
            log = cl.read()

        self.process_h2_regions(log, 2, version)

    def set_css(self):
        base_font_size = self.html.css_rules['body']['font-size']
        self.html.css_rules['body']['padding'] = '20px'
        self.html.css_rules['h2'] = {'font-size': self.html.get_font_size(base_font_size, 0.4), 'color': '#81CFE0'}
        self.html.css_rules['h3'] = {'font-size': self.html.get_font_size(base_font_size, 0.2), 'font-weight': 'none'}
        self.html.css_rules['h4'] = {'font-size': self.html.get_font_size(base_font_size, 0.1), 'font-weight': 'none'}
        self.html.css_rules['h5'] = {'font-size': self.html.get_font_size(base_font_size, 0.1), 'font-weight': 'bold'}
        self.html.css_rules['.kbd'] = {'color': '#A6C8AA', 'font-weight': 'bold', 'font-size': self.html.get_font_size(base_font_size, 0.1)}
        self.html.css_rules['.success2'] = {'padding': '5px', 'color': self.html.css_rules['.success']['color']}
        self.html.css_rules['.undefined'] = {'padding': '5px', 'color': '#c0c0c0'}
        self.html.css_rules['.command'] = {'color': '#7D9DF8', 'font-weight': 'bold'}
        self.html.css_rules['.snippet'] = {'color': '#8CCAC8', 'font-weight': 'none'}
        self.html.css_rules['.property'] = {'color': '#A2DED0', 'font-weight': 'none'}
        self.html.css_rules['.tag'] = {'color': '#FDE3A7', 'font-weight': 'none'}
        self.html.css_rules['.note_base'] = {
            'background-color': '#0F4026',
            'border-radius': '4px',
            'margin': '1rem'
        }
        self.html.css_rules['.note_head'] = {
            'border-top-left-radius': '4px',
            'border-top-right-radius': '4px',
            'padding': '0.2rem 0.2rem 0.2rem 0.7rem',
            'display': 'block',
            'background-color': '#83C6A3',
            'color': '#0F4026',
            'font-weight': 'bold'
        }
        self.html.css_rules['.note'] = {
            'color': '#c8f7c5',
            'border-bottom-left-radius': '4px',
            'border-bottom-right-radius': '4px',
            'padding': '0.7rem',
            'display': 'block'
        }

    def process_h2_regions(self, data, level, version):
        # group 1: header name
        # group 2: header data

        data = self.process_urls(data)
        data = self.process_kbd(data)
        data = self.process_templates(data)
        data = self.process_src(data)
        data = self.process_decoration(data)
        data = self.process_headers(data, 3)
        data = self.process_headers(data, 4)
        data = self.process_headers(data, 5)
        data = self.process_lists(data)

        blocks = []
        pattern = r'^={%(level)s}([^=]+)={%(level)s}\s?\n((.|\n)*?)(?=(^={%(level)s}[^=]|\Z))' % {'level': level}
        headers = reversed(re.findall(pattern, data, re.MULTILINE))
        if headers:
            for r in headers:
                blocks.append(self.html.h2(r[0]))
                blocks.append(r[1])
        html = self.html.build(blocks)

        if version == 'sublime':
            view = sublime.active_window().new_file()
            view.set_name('{} changelog'.format(utils.p.PM))
            view.settings().set('gutter', False)
            view.settings().set('word_wrap', True)
            view.settings().set('wrap_width', 120)
            view.add_phantom('changelog', view.sel()[0], html, sublime.LAYOUT_INLINE, on_navigate=self.on_navigate)
            view.set_scratch(True)
        elif version == 'browser':
            preview_file = utils.p.from_package('{}_changelog.html'.format(utils.p.PML), name='User', posix=False, is_abs=True)
            html = html.replace('<html>', '<html><head><meta charset="UTF-8"/></head>')
            with open(preview_file, 'w', encoding='utf-8') as tf:
                tf.write(html)

            webbrowser.open('file://{}'.format(tf.name))

    def on_navigate(self, url):
        webbrowser.open(url)

    def escape(self, line):
        return line.replace(' ', '&nbsp;').replace('<', '&lt;').replace('>', '&gt;')

    def process_urls(self, data):

        def url(m):
            if not m.group(2):
                url_name = m.group(1)
            else:
                url_name = m.group(2)
            return self.html.link(m.group(1), url_name)

        lines = []
        pattern = r'\[{1}([^\[\]]+?)\s([^\[\]]+)?\]{1}'
        for line in data.splitlines():
            line = re.sub(pattern, url, line)
            lines.append(line)
        return '\n'.join(lines)

    def process_kbd(self, data):
        ''' <kbd> => <tt> '''
        lines = []
        for line in data.splitlines():
            line = line.replace('<kbd>', '<tt class="kbd">').replace('</kbd>', '</tt>')
            lines.append(line)
        return '\n'.join(lines)

    def process_templates(self, data):
        ''' templates => plugin commands '''

        def repl(m):
            return self.html.code(m.group(2), css_class=m.group(1).lower()) if m else ''

        def repl_note(m):

            return self.html.note('Note', m.group(2)) if m else ''

        lines = []
        # pattern = r'\{{2}(%s)\|([^\{\}]+)\}{2}'
        pattern = r'\{{2}(%s)\|([^\{\}]+)\}{2}'

        for line in data.splitlines():
            line = re.sub(pattern % 'Command', repl, line)
            line = re.sub(pattern % 'Snippet', repl, line)
            line = re.sub(pattern % 'Property', repl, line)
            line = re.sub(pattern % 'Tag', repl, line)
            line = re.sub(pattern % 'Note', repl_note, line)
            lines.append(line)
        return '\n'.join(lines)

    def process_src(self, data):
        lines = []
        lines_src = []
        is_source = False
        for line in data.splitlines():

            if line.startswith('<source') and line.endswith('">'):
                is_source = True
                continue
            if line.startswith('</source>'):
                is_source = False
                src = '\n<br>'.join(lines_src)
                lines_src = []
                lines.append(self.html.note('Source', src, code=True))
                continue

            if is_source:
                lines_src.append(self.escape(line))
            else:
                lines.append(line)

        return '\n'.join(lines)

    def process_headers(self, data, lvl):
        lines = []
        pattern = r'^={%(level)s}([^=]+)={%(level)s}\s?$' % {'level': lvl}

        for line in data.splitlines():
            header = re.search(pattern, line)
            if header:
                h = header.group(1)
                line = self.html.h(lvl, h)
            lines.append(line)

        return '\n'.join(lines)

    def process_decoration(self, data):
        lines = []
        pattern_b = r'\'{3}([^\']+)\'{3}'
        pattern_i = r'\'{2}([^\']+)\'{2}'

        for line in data.split('\n'):
            line = re.sub(pattern_b, self.html.b(r'\1'), line)
            line = re.sub(pattern_i, self.html.i(r'\1'), line)
            lines.append(line)

        return '\n'.join(lines)

    def process_lists(self, data):
        lines = []
        lvl = 0
        for line in data.splitlines():
            if line.startswith(('*', ':')):
                line_lvl = len(line) - len(line.lstrip('*:'))
                if line_lvl > lvl:
                    # TODO: make sub uls inside li tag
                    # lines.append('<li>') if line_lvl > 1 else ''
                    lines.append(self.html.ul())
                elif line_lvl < lvl:
                    lines.append(self.html.ul(True))
                    # lines.append('</li>') if lvl > 1 else ''
                lvl = line_lvl
                if line.startswith('*'):
                    line = self.html.li(line[line_lvl:].strip(), icon=self.LIST_ICON, css_class='undefined')
                elif line.startswith(':'):
                    line = self.html.li(line[line_lvl:].strip(), icon=None)
            else:
                if lvl and not line.startswith(('*', ':')):
                    lines.append(self.html.ul(True) * lvl)
                    lvl = 0
            lines.append(line)

        if lvl:
            lines.append(self.html.ul(True) * lvl)
        return '\n'.join(lines)
