#!/usr/bin/env python\n
# -*- coding: utf-8 -*-

import sys
import sublime
import sublime_plugin

pythonver = sys.version_info[0]

if pythonver >= 3:
    from . import mw_utils as mw
    from distutils.util import strtobool
    from collections import OrderedDict


class MWHTML(object):

    HTML_HEADER = '''
    <html>
        <body id="mediawiker_html">
            <style>
                html { padding: 0; margin: 0; background-color: %(html_background_color)s; }

                body { padding: 0; margin: 0; font-family: Tahoma; color: %(body_color)s;}

                div { display: block; }

                a {text-decoration: none; font-size: 1.2rem; color: %(a_color)s; }

                ul { padding-right: 2rem; }

                li {margin-left: 0; display: block; font-size: 1.2rem; }

                code {color: %(code_color)s; }

                h1, h2, h3, h4 {margin: 2rem; color: %(h_color)s; }

                .error {padding: 5px; color: %(class_error_color)s; }

                .success {padding: 5px; color: %(class_success_color)s; }

            </style>
            <div id="mediawiker_html">
    '''
    HTML_FOOTER = '''
            </div>
        </body>
    </html>
    '''
    config = {}

    def __init__(self, **kwargs):
        self.config['html_background_color'] = kwargs.get('html_background_color', '#2c3e50') or '#2c3e50'
        self.config['body_color'] = kwargs.get('body_color', 'white') or 'white'
        self.config['a_color'] = kwargs.get('a_color', '#C5EFF7') or '#C5EFF7'
        self.config['code_color'] = kwargs.get('code_color', '#c0c0c0') or '#c0c0c0'
        self.config['h_color'] = kwargs.get('h_color', '#DADFE1') or '#DADFE1'
        self.config['class_error_color'] = kwargs.get('class_error_color', '#c0392b') or '#c0392b'
        self.config['class_success_color'] = kwargs.get('class_success_color', '#27ae60') or '#27ae60'

    def h(self, lvl, title):
        return '<h%(level)s>%(title)s</h%(level)s>' % {
            'level': lvl,
            'title': title
        }

    def h2(self, title):
        return self.h(2, title)

    def link(self, url, text):
        return '<a href="%s">%s</a>' % (url, text)

    def ul(self, close=False):
        return '<ul>' if not close else '</ul>'

    def li(self, data):
        return '<li>%s</li>' % data

    def strong(self, data, css_class='success'):
        return '<strong class="%s">%s</strong>' % (css_class, data)

    def code(self, data):
        return '<code>%s</code>' % data

    def build(self, lines):
        return "%s\n%s\n%s" % (self.HTML_HEADER % self.config, '\n'.join(lines), self.HTML_FOOTER)


class MediawikerConfiguratorCommand(sublime_plugin.TextCommand):

    MENU = [
        'Select wiki',
        'Preferences',
        'Edit panel',
        'Tab options'
    ]

    FORMAT_SECTION = '%(name)s'
    FORMAT_OPTION = '%(status)s %(name)s'
    FORMAT_URL = '%(section)s:%(value)s:%(params)s:%(goto)s'
    MENU_OFFSET = 20

    def run(self, edit):
        self.MARKED = mw.get_setting('mediawiker_config_icon_checked', '✓')
        self.UNMARKED = mw.get_setting('mediawiker_config_icon_unchecked', '✗')
        self.RADIO_MARKED = mw.get_setting('mediawiker_config_icon_radio_checked', '✓')
        self.RADIO_UNMARKED = mw.get_setting('mediawiker_config_icon_radio_unchecked', '⭕')
        self.EDIT_ICON = mw.get_setting('mediawiker_config_icon_edit', '🖉')

        config_html = mw.get_setting('mediawiker_config_html', {})
        self.html = MWHTML(**config_html)

        if pythonver < 3:
            sublime.message_dialog('Only Sublime Text 3 supported')
            return

        self.show()

    def post_prepare_menu(self, section, menu):
        if not section == 'Main':

            link = self.html.link(
                url=self.FORMAT_URL % {'section': 'BACK', 'value': 'BACK', 'params': '', 'goto': 'Main'},
                text=self.FORMAT_SECTION % {'name': '%s Back' % self.icon('←')}
            )
            menu.append(self.html.li(link))
        return menu

    def append_toggle(self, menu, name, status, value, section, params, goto, adv=None):
        if adv is None:
            adv = ''

        link = self.html.link(
            url=self.FORMAT_URL % {'section': section, 'value': value, 'params': params, 'goto': goto},
            text=self.FORMAT_OPTION % {'status': status, 'name': name}
        )
        menu.append(self.html.li('%s%s' % (link, adv)))
        return menu

    def icon(self, icon, css_class='success'):
        return self.html.strong(icon, css_class)

    def pretty(self, value):
        return ' '.join(value.replace('mediawiker_', '').replace('mediawiki_', '').split('_')).capitalize()

    def prepare_menu_edit_panel(self, section, menu):

        menu.append(self.html.ul())
        menu = self.append_toggle(menu=menu, name='[All turn ON]', status=self.icon(self.MARKED, 'success'), value='all_on', section=section, params=0, goto=section)
        menu = self.append_toggle(menu=menu, name='[All turn OFF]', status=self.icon(self.UNMARKED, 'error'), value='all_off', section=section, params=0, goto=section)

        self.options_default = mw.get_default_setting('mediawiker_panel', [])
        self.options = mw.get_setting('mediawiker_panel', None)
        snippet_char = mw.get_setting('mediawiker_snippet_char', 'Snippet:')
        if self.options is None:
            self.options = self.options_default

        for idx, option in enumerate(self.options_default):
            option_value = True if option in self.options else False
            option_text = '%s %s' % (snippet_char, option.get('caption')) if option.get('type') == 'snippet' else option.get('caption')
            menu = self.append_toggle(menu=menu, name=option_text,
                                      status=self.icon(self.MARKED if option_value else self.UNMARKED, 'success' if option_value else 'error'),
                                      value=not option_value, section=section, params=idx, goto=section)
        else:
            menu = self.post_prepare_menu(section, menu)
            menu.append(self.html.ul(close=True))

        return menu

    def show(self, section='Main'):

        popup = []
        if section == 'Main':

            popup.append(self.html.h2('Mediawiker'))

            popup.append(self.html.ul())
            for option in self.MENU:
                link = self.html.link(
                    url=self.FORMAT_URL % {'section': section, 'value': '', 'params': '', 'goto': option},
                    text=self.FORMAT_SECTION % {'name': option}
                )
                popup.append(self.html.li(link))
            else:
                popup.append(self.html.ul(False))

        elif section == 'Edit panel':
            popup.append(self.html.h2('Edit panel'))
            popup = self.prepare_menu_edit_panel(section=section, menu=popup)

        elif section == 'Preferences':
            popup.append(self.html.h2('Preferences'))
            settings_default = sublime.decode_value(sublime.load_resource('Packages/Mediawiker/Mediawiker.sublime-settings'))

            popup.append(self.html.ul())
            for idx, option in enumerate(settings_default):
                value = mw.get_setting(option)
                option_pretty = self.pretty(option)
                if isinstance(settings_default.get(option, None), bool):
                    popup = self.append_toggle(menu=popup, name=option_pretty,
                                               status=self.icon(self.MARKED if value else self.UNMARKED, 'success' if value else 'error'),
                                               value=not value, section=section, params='%s/bool' % (option), goto=section)
                elif not isinstance(settings_default.get(option, None), list) and not isinstance(settings_default.get(option, None), dict):
                    option_pretty = self.pretty(option)
                    if isinstance(settings_default.get(option, None), int):
                        value_pretty = '"%s"' % self.html.code(value)
                        option_type = 'int'
                    else:
                        option_type = 'text'
                        value_pretty = '"%s"' % self.html.code(value) if value else '""'
                        value = self.escaped(value)
                    popup = self.append_toggle(menu=popup, name='%s: %s' % (option_pretty, value_pretty), status=self.icon('•'),
                                               value=value, section=section, params='%s/%s' % (option, option_type),
                                               goto=self.escaped(section))
            else:
                popup = self.post_prepare_menu(section, popup)
                popup.append(self.html.ul(False))

        elif section == 'Select wiki':
            popup.append(self.html.h2('Select wiki'))
            sites = mw.get_setting('mediawiki_site')
            site_active = mw.get_view_site()

            popup.append(self.html.ul())
            for site in sites.keys():
                link = self.html.link(
                    url=self.FORMAT_URL % {'section': section, 'value': 'edit', 'params': self.escaped(site), 'goto': 'Edit site/%s' % self.escaped(site)},
                    text=self.icon(self.EDIT_ICON)
                )
                adv = '&nbsp;&nbsp;%s' % (link)
                popup = self.append_toggle(menu=popup, name=site,
                                           status=self.icon(self.RADIO_MARKED if site == site_active else self.RADIO_UNMARKED, 'success' if site == site_active else 'error'),
                                           value='', section=section, params=self.escaped(site), goto=section, adv=adv)
            else:
                popup = self.post_prepare_menu(section, popup)
                popup.append(self.html.ul(False))

        elif section.startswith('Edit site'):
            popup.append(self.html.h2('Edit site'))
            section_clear, site = section.split('/')
            settings = mw.get_setting('mediawiki_site').get(site)
            settings_default = OrderedDict([
                ('host', (False, '')),
                ('https', (True, True)),
                ('is_ssl_cert_verify', (True, True)),
                ('path', (False, '')),
                ('pagepath', (False, '')),
                ('domain', (False, '')),
                ('username', (False, '')),
                ('password', (False, '')),
                ('use_http_auth', (True, False)),
                ('http_auth_login', (False, '')),
                ('http_auth_password', (False, '')),
                ('proxy_host', (False, '')),
                ('oauth_access_secret', (False, '')),
                ('oauth_access_token', (False, '')),
                ('oauth_consumer_secret', (False, '')),
                ('oauth_consumer_token', (False, '')),
                ('authorization_type', (False, 'login')),
                ('cookies_browser', (False, 'chrome'))
            ])

            popup.append(self.html.ul())
            for option in settings_default.keys():
                option_pretty = self.pretty(option)
                value = settings.get(option, settings_default.get(option)[1])
                if settings_default.get(option)[0]:
                    # boolean type
                    popup = self.append_toggle(menu=popup, name=option_pretty,
                                               status=self.icon(self.MARKED if value else self.UNMARKED, 'success' if value else 'error'),
                                               value=not value, section=section_clear, params='%s/%s/bool' % (self.escaped(site), option), goto=section)
                else:
                    if option.endswith(('password', 'secret', 'token')):
                        option_type = 'passwd'
                        value_pretty = mw.get_setting('mediawiker_password_char', '*') * 8 if value else '""'
                    else:
                        option_type = 'text'
                        value_pretty = '"%s"' % self.html.code(value) if value else '""'

                    popup = self.append_toggle(menu=popup, name='%s: %s' % (option_pretty, value_pretty), status=self.icon('•'),
                                               value=self.escaped(value), section=section_clear, params='%s/%s/%s' % (self.escaped(site), option, option_type),
                                               goto=self.escaped(section))
            else:
                popup = self.post_prepare_menu(section, popup)
                popup.append(self.html.ul(False))

        elif section == 'Tab options':
            popup.append(self.html.h2('Tab options'))
            settings = self.view.settings()

            settings_default = OrderedDict([
                ('mediawiker_is_here', (True, False)),
                ('mediawiker_wiki_instead_editor', (True, False)),
                ('mediawiker_site', (False, '')),
                ('page_revision', (False, ''))
            ])

            popup.append(self.html.ul())
            for option in settings_default.keys():
                option_pretty = self.pretty(option)
                if settings_default.get(option)[0]:
                    value = settings.get(option, settings_default.get(option)[1])
                    popup = self.append_toggle(menu=popup, name=option_pretty,
                                               status=self.icon(self.MARKED if value else self.UNMARKED, 'success' if value else 'error'),
                                               value=not value, section=section, params=option, goto=section)
                else:
                    value = settings.get(option, '')
                    line = self.html.li('%s %s: %s' % (self.icon('•'), option_pretty, '"%s"' % self.html.code(value) if value else '""'))
                    popup.append(line)
            else:
                popup = self.post_prepare_menu(section, popup)
                popup.append(self.html.ul(False))

        self.show_menu(popup)

    def show_menu(self, popup):
        if not popup:
            return

        print(self.html.build(popup))

        self.view.show_popup(
            content=self.html.build(popup),
            flags=0,
            location=self.view.visible_region().a + self.MENU_OFFSET,
            max_width=800,
            max_height=600,
            on_navigate=self.on_navigate,
            on_hide=None)

    def escaped(self, value):
        return value.replace(':', '>>')

    def unescaped(self, value):
        return value.replace('&gt;&gt;', ':')

    def toggle_edit_panel(self, value, idx):
        elem = self.options_default[idx]
        if value == 'all_on':
            mw.del_setting('mediawiker_panel')
        else:
            if value == 'all_off':
                self.options = []
            elif strtobool(value) and elem not in self.options:
                self.options.append(elem)
            elif elem in self.options:
                self.options.remove(elem)
            mw.set_setting('mediawiker_panel', self.options)

    def on_navigate(self, url):

        section, value, params, goto = [self.unescaped(val) for val in url.split(':')]
        is_async = False
        if section == 'Edit panel':
            idx = int(params)
            self.toggle_edit_panel(value, idx)
        elif section == 'Preferences':
            option, option_type = params.split('/')
            if option_type == 'bool':
                mw.set_setting(option, True if strtobool(value) else False)
            elif option_type in ('text', 'int'):
                is_async = True
                option_pretty = self.pretty(option)
                panel = InputValue(option=option, goto=goto, callback=self.show, option_type=option_type)
                panel.show_input(panel_title=option_pretty, value_pre=value)
        elif section == 'Select wiki':
            if value != 'edit':
                if self.view.settings().get('mediawiker_is_here', False):
                    self.view.settings().set('mediawiker_site', params)
                mw.set_setting("mediawiki_site_active", params)
        elif section == 'Edit site':
            site, option, option_type = params.split('/')
            if option_type == 'bool':
                settings = mw.get_setting('mediawiki_site')
                settings[site][option] = True if strtobool(value) else False
                mw.set_setting('mediawiki_site', settings)
            elif option_type in ('text', 'passwd'):
                is_async = True
                option_pretty = self.pretty(option)
                panel = InputSiteValue(site=site, option=option, goto=goto, callback=self.show)
                if option_type == 'text':
                    panel.show_input(panel_title=option_pretty, value_pre=value)
                elif option_type == 'passwd':
                    panel.show_input_passwd(value_pre=value)
        elif section == 'Tab options':
            self.view.settings().set(params, True if strtobool(value) else False)

        if not is_async:
            self.show(goto)


class InputValue(mw.InputPanel):

    def __init__(self, option, goto, callback, option_type='text'):
        super(InputValue, self).__init__()
        self.option = option
        self.goto = goto
        self.callback = callback
        self.option_type = option_type

    def on_done(self, value):
        self.value = int(value) if self.option_type == 'int' else value
        self.set_setting()

    def on_cancel(self):
        self.callback(self.goto)

    def set_setting(self):
        mw.set_setting(self.option, self.value)
        self.callback(self.goto)


class InputSiteValue(mw.InputPanel):

    def __init__(self, site, option, goto, callback):
        super(InputSiteValue, self).__init__()
        self.site = site
        self.option = option
        self.goto = goto
        self.callback = callback
        self.ph = None

    def show_input_passwd(self, value_pre):
        self.ph = mw.PasswordHider()
        password = self.ph.hide(value_pre)
        self.show_input(panel_title='Password', value_pre=password)

    def on_change(self, str_val):
        if str_val and self.ph:
            password = self.ph.hide(str_val)
            if password != str_val:
                self.show_input('Password:', password)

    def on_done(self, value):
        self.value = value if not self.ph else self.ph.done()
        self.set_setting()

    def on_cancel(self):
        self.callback(self.goto)

    def set_setting(self):
        settings = mw.get_setting('mediawiki_site')
        settings[self.site][self.option] = self.value if self.value is not None else ''
        mw.set_setting('mediawiki_site', settings)
        self.callback(self.goto)
