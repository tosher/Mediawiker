#!/usr/bin/env python\n
# -*- coding: utf-8 -*-

import sublime
# import sublime_plugin
from . import mw_utils as utils
from collections import OrderedDict


class MwHtml(object):

    HTML_HEADER = ''' \
    <html>
        <body id="{html_id}">
            <style>
                {style_css}
            </style>
            <div>
    '''
    HTML_FOOTER = ''' \
            </div>
        </body>
    </html>
    '''

    debug = False

    def __init__(self, html_id, user_css=True):
        self.html_id = html_id
        self.user_css = user_css
        self.css_rules = OrderedDict([
            ('html', {'padding': '0', 'margin': '0', 'background-color': '#19232D'}),
            ('body', {'padding': '0', 'margin': '0', 'font-family': 'Helvetica, Arial, Tahoma', 'color': 'white', 'font-size': '1rem'}),
            ('div', {'display': 'block'}),
            ('a', {'text-decoration': 'underline', 'color': '#8FC1FF', 'font-size': '1rem'}),
            ('ul', {'padding-left': '1rem'}),
            ('li', {'margin-left': '1rem', 'display': 'block', 'font-size': '1rem'}),
            ('code', {'padding': '0.1rem', 'color': '#c0c0c0', 'font-size': '1.1rem'}),
            ('h1,h2,h3,h4', {'margin-bottom': '1rem', 'color': '#C2E0C2'}),
            ('.error', {'padding': '5px', 'color': '#c0392b'}),
            ('.success', {'padding': '5px', 'color': '#27ae60'})
        ])

    def debug_html(self, html):
        view = sublime.active_window().new_file()
        view.set_name('debug.html')
        view.set_syntax_file(utils.p.from_package('HTML.sublime-syntax', name='HTML'))
        view.run_command(utils.cmd('insert_text'), {'position': 0, 'text': html, 'with_erase': True})
        view.set_scratch(True)

    # def set_css(self, rule, value, attr=None):
    #     if not attr:
    #         self.css_rules[rule] = value
    #     else:
    #         self.css_rules[rule][attr] = value

    def get_user_css(self):
        css_user = utils.props.get_setting('css_html', {})
        if css_user:
            for key in css_user.keys():
                for tag in css_user[key].keys():
                    if key in self.css_rules:
                        if tag in self.css_rules[key]:
                            self.css_rules[key][tag] = css_user[key][tag]

    def build_css(self):
        lines = []
        if self.user_css:
            self.get_user_css()
        for rule in self.css_rules.keys():
            lines.append('%s { %s; }' % (rule, '; '.join(['%s: %s' % (k, v) for k, v in self.css_rules[rule].items()])))

        return '\n'.join(lines)

    def get_font_size(self, size, delta):
        font_size = float(size.replace('rem', ''))
        return '%srem' % round(font_size + delta, 1)

    def h(self, lvl, title, css_class=None):
        if css_class is None:
            return '<h{level}>{title}</h{level}>'.format(
                level=lvl,
                title=title
            )
        else:
            return '<h{level} class="{css_class}">{title}</h{level}>'.format(
                level=lvl,
                title=title,
                css_class=css_class
            )

    def h2(self, title, css_class=None):
        return self.h(2, title, css_class)

    def link(self, url, text, css_class=None):
        if not css_class:
            return '<a href="{}">{}</a>'.format(url, text)
        else:
            return '<a href="{}" class="{}">{}</a>'.format(url, css_class, text)

    def a(self, url, text, css_class=None):
        ''' just alias to link '''
        return self.link(url, text, css_class)

    def simple_tag(self, tag, text, css_class=None, close=True):
        if close:
            close_tag = '</{tag}>'.format(tag=tag)
        if not css_class:
            return '<{tag}>{text}{close_tag}'.format(tag=tag, text=text, close_tag=close_tag)
        else:
            return '<{tag} class="{css_class}">{text}{close_tag}'.format(tag=tag, text=text, css_class=css_class, close_tag=close_tag)

    def ul(self, close=False):
        return '<ul>' if not close else '</ul>'

    def li(self, data, icon='•', css_class=None, close=True):
        text = self.join(self.span(icon, css_class=css_class) if icon else '', data)
        return self.simple_tag('li', text, close=close)

    def b(self, data, close=True):
        return self.simple_tag('b', data, close=close)

    def i(self, data, close=True):
        return self.simple_tag('i', data, close=close)

    def strong(self, data, css_class=None, close=True):
        return self.simple_tag('strong', data, css_class=css_class, close=close)

    def var(self, data, css_class=None, close=True):
        return self.simple_tag('var', data, css_class=css_class, close=close)

    def div(self, data, css_class=None, close=True):
        return self.simple_tag('div', data, css_class=css_class, close=close)

    def span(self, data, css_class=None, close=True):
        return self.simple_tag('span', data, css_class=css_class, close=close)

    def tt(self, data, css_class=None, close=True):
        return self.simple_tag('tt', data, css_class=css_class, close=close)

    def code(self, data, css_class=None, close=True):
        return self.simple_tag('code', data, css_class=css_class, close=close)

    def img(self, uri):
        if not uri:
            return ''
        return '<img src="{}">'.format(uri)

    def br(self, cnt=1):
        return '<br>' * cnt

    # python 3
    # def join(self, *args, char=' '):
    #     return char.join([a for a in args if a])

    def join(self, *args, **kwargs):
        char = kwargs.get('char', ' ')
        return char.join([a for a in args if a])

    def build(self, lines):

        html = "{}\n{}\n{}".format(self.HTML_HEADER.format(html_id=self.html_id, style_css=self.build_css()), '\n'.join(lines), self.HTML_FOOTER)
        if self.debug:
            self.debug_html(html)
        return html


class MwHtmlAdv(MwHtml):

    def __init__(self, html_id, user_css=True):
        super(MwHtmlAdv, self).__init__(html_id=html_id, user_css=user_css)

    # python 3
    # def unnumbered_list(self, *items, icon='•', css_class=None):
    #     li_list = []
    #     li_list.append(self.ul())
    #     for li in items:
    #         li_list.append(self.li(li, icon=icon, css_class=css_class))
    #     li_list.append(self.ul(close=True))
    #     return '\n'.join(li_list)

    def unnumbered_list(self, *items, **kwargs):
        icon = kwargs.get('icon', '•')
        css_class = kwargs.get('css_class', None)
        li_list = []
        li_list.append(self.ul())
        for li in items:
            li_list.append(self.li(li, icon=icon, css_class=css_class))
        li_list.append(self.ul(close=True))
        return '\n'.join(li_list)

    def note(self, title, msg, code=False):
        return '\n'.join([
            '<div class="note_base">',
            '   <div class="note_head">',
            '       {title}'.format(title=title),
            '   </div>',
            '   <div class="note">',
            '       <code style="font-size: {font_size}">'.format(font_size=self.get_font_size(self.css_rules['code']['font-size'], -0.3)) if code else '',
            '       {msg}'.format(msg=msg),
            '       </code>' if code else '',
            '   </div>',
            '</div>'
        ])

    def with_border(self, elem, border, color='#c0c0c0'):
        return '<div style="padding: {border}spx; background-color: {color};">{elem}</div>'.format(
            border=border,
            color=color,
            elem=elem
        )
