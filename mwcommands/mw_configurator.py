#!/usr/bin/env python\n
# -*- coding: utf-8 -*-

import sys
import sublime
import sublime_plugin

pythonver = sys.version_info[0]

if pythonver >= 3:
    import mdpopups
    from . import mw_utils as mw
    from distutils.util import strtobool
    from collections import OrderedDict
else:
    import mw_utils as mw

STYLES = '''
body {
    padding: 8px;
    font-family: Tahoma;
}

a {
    text-decoration: none;
    font-size: {{'+7px'|relativesize}};
}
li {
    margin-left: 0;
    display: block;
    font-size: {{'+7px'|relativesize}};
}

.mediawiker {
    margin-left: 2rem;
}

h1, h2, h3, h4 {
    margin: 2rem;
}

'''


class MediawikerConfiguratorCommand(sublime_plugin.TextCommand):

    MENU = [
        'Select wiki',
        'Preferences',
        'Edit panel',
        'Tab options'
    ]

    OPTION = '- [%(status)s %(name)s](%(section)s:%(value)s:%(params)s:%(goto)s)%(adv)s\n'
    SECTION = '- [%(name)s](%(section)s:%(value)s:%(params)s:%(goto)s)\n'
    MENU_OFFSET = 20
    MARKED = '✓'
    UNMARKED = '✗'
    RADIO_MARKED = '✔'
    RADIO_UNMARKED = '⭕'

    def run(self, edit):

        if pythonver < 3:
            sublime.message_dialog('Only Sublime Text 3 supported')
            return

        self.show()

    def post_prepare_menu(self, section, menu):
        if not section == 'Main':
            menu.append(
                self.SECTION % {
                    'name': '%s Back' % self.icon('←'),
                    'value': 'BACK',
                    'section': 'BACK',
                    'params': '',
                    'goto': 'Main'
                }
            )
        return menu

    def append_toggle(self, menu, name, status, value, section, params, goto, adv=None):
        if adv is None:
            adv = ''
        menu.append(
            self.OPTION % {
                'name': name,
                'status': status,
                'value': value,
                'section': section,
                'params': params,
                'goto': goto,
                'adv': adv
            }
        )
        return menu

    def icon(self, icon, css_class='.success'):
        return '**%s**{: %s}' % (icon, css_class)

    def pretty(self, value):
        return ' '.join(value.replace('mediawiker_', '').replace('mediawiki_', '').split('_')).capitalize()

    def prepare_menu_edit_panel(self, section, menu):

        menu = self.append_toggle(menu=menu, name='[All turn ON]', status=self.icon(self.MARKED, '.success'), value='all_on', section=section, params=0, goto=section)
        menu = self.append_toggle(menu=menu, name='[All turn OFF]', status=self.icon(self.UNMARKED, '.error'), value='all_off', section=section, params=0, goto=section)

        self.options_default = mw.get_default_setting('mediawiker_panel', [])
        self.options = mw.get_setting('mediawiker_panel', None)
        if self.options is None:
            self.options = self.options_default

        for idx, option in enumerate(self.options_default):
            option_value = True if option in self.options else False
            option_text = option.get('caption')
            menu = self.append_toggle(menu=menu, name=option_text,
                                      status=self.icon(self.MARKED if option_value else self.UNMARKED, '.success' if option_value else '.error'),
                                      value=not option_value, section=section, params=idx, goto=section)

        return menu

    def show(self, section='Main'):

        popup = []
        if section == 'Main':

            popup.append('## Mediawiker\n')

            for option in self.MENU:
                popup.append(
                    self.SECTION % {
                        'name': option,
                        'value': '',
                        'section': section,
                        'params': '',
                        'goto': option
                    }
                )

        elif section == 'Edit panel':
            popup.append('## Edit panel\n')
            popup = self.prepare_menu_edit_panel(section=section, menu=popup)

        elif section == 'Preferences':
            popup.append('## Preferences\n')
            settings_default = sublime.decode_value(sublime.load_resource('Packages/Mediawiker/Mediawiker.sublime-settings'))
            for idx, option in enumerate(settings_default):
                value = mw.get_setting(option)
                option_pretty = self.pretty(option)
                if isinstance(settings_default.get(option, None), bool):
                    popup = self.append_toggle(menu=popup, name=option_pretty,
                                               status=self.icon(self.MARKED if value else self.UNMARKED, '.success' if value else '.error'),
                                               value=not value, section=section, params='%s/bool' % (option), goto=section)
                elif not isinstance(settings_default.get(option, None), list) and not isinstance(settings_default.get(option, None), dict):
                    option_pretty = self.pretty(option)
                    if isinstance(settings_default.get(option, None), int):
                        value_pretty = '`%s`' % value
                        option_type = 'int'
                    else:
                        option_type = 'text'
                        value_pretty = '"`%s`"' % value if value else '""'
                        value = self.escaped(value)
                    popup = self.append_toggle(menu=popup, name='%s: %s' % (option_pretty, value_pretty), status=self.icon('•'),
                                               value=value, section=section, params='%s/%s' % (option, option_type),
                                               goto=self.escaped(section))

        elif section == 'Select wiki':
            popup.append('## Select wiki\n')
            sites = mw.get_setting('mediawiki_site')
            site_active = mw.get_view_site()
            for site in sites.keys():
                adv = '&nbsp;&nbsp;[%s](%s:%s:%s:Edit site/%s){: .mediawiker-control }' % (self.icon('🖉'), section, 'edit', self.escaped(site), self.escaped(site))  # TODO
                popup = self.append_toggle(menu=popup, name=site,
                                           status=self.icon(self.RADIO_MARKED if site == site_active else self.RADIO_UNMARKED, '.success' if site == site_active else '.error'),
                                           value='', section=section, params=self.escaped(site), goto=section, adv=adv)
        elif section.startswith('Edit site'):
            popup.append('## Edit site\n')
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
                ('oauth_consumer_token', (False, ''))
            ])

            for option in settings_default.keys():
                option_pretty = self.pretty(option)
                value = settings.get(option, settings_default.get(option)[1])
                if settings_default.get(option)[0]:
                    # boolean type
                    popup = self.append_toggle(menu=popup, name=option_pretty,
                                               status=self.icon(self.MARKED if value else self.UNMARKED, '.success' if value else '.error'),
                                               value=not value, section=section_clear, params='%s/%s/bool' % (self.escaped(site), option), goto=section)
                else:
                    if option.endswith(('password', 'secret', 'token')):
                        option_type = 'passwd'
                        value_pretty = mw.get_setting('mediawiker_password_char', '*') * 8 if value else '""'
                    else:
                        option_type = 'text'
                        value_pretty = '"`%s`"' % value if value else '""'

                    popup = self.append_toggle(menu=popup, name='%s: %s' % (option_pretty, value_pretty), status=self.icon('•'),
                                               value=self.escaped(value), section=section_clear, params='%s/%s/%s' % (self.escaped(site), option, option_type),
                                               goto=self.escaped(section))

        elif section == 'Tab options':
            popup.append('## Tab options\n')
            settings = self.view.settings()

            settings_default = OrderedDict([
                ('mediawiker_is_here', (True, False)),
                ('mediawiker_wiki_instead_editor', (True, False)),
                ('mediawiker_site', (False, '')),
                ('page_revision', (False, ''))
            ])

            for option in settings_default.keys():
                option_pretty = self.pretty(option)
                if settings_default.get(option)[0]:
                    value = settings.get(option, settings_default.get(option)[1])
                    popup = self.append_toggle(menu=popup, name=option_pretty,
                                               status=self.icon(self.MARKED if value else self.UNMARKED, '.success' if value else '.error'),
                                               value=not value, section=section, params=option, goto=section)
                else:
                    value = settings.get(option, '')
                    popup.append('- %s %s: %s\n' % (self.icon('•'), option_pretty, '"`%s`"' % value if value else '""'))

        popup = self.post_prepare_menu(section, popup)
        self.show_menu(popup)

    def show_menu(self, popup):
        if not popup:
            return

        mdpopups.show_popup(
            self.view,
            ''.join(popup),
            css=STYLES,
            on_navigate=self.on_navigate,
            max_width=800,
            max_height=800,
            location=self.view.visible_region().a + self.MENU_OFFSET,
            flags=sublime.HIDE_ON_MOUSE_MOVE_AWAY
        )

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
