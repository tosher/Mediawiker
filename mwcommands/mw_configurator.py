#!/usr/bin/env python\n
# -*- coding: utf-8 -*-

try:
    import json
except ImportError:
    import simplejson as json

import sublime
import sublime_plugin
from . import mw_utils as utils
from . import mw_html


class MediawikerConfiguratorCommand(sublime_plugin.TextCommand):

    MENU = [
        'Select wiki',
        'Preferences',
        'Edit panel',
        'Tab options'
    ]

    FORMAT_SECTION = '%(name)s'
    FORMAT_OPTION = '%(status)s %(name)s'
    TYPE_PASSWORD = 'passwd'
    PROPERTY_SITE_NAME = 'name'

    def run(self, edit):
        self.MARKED = utils.props.get_setting('config_icon_checked')
        self.UNMARKED = utils.props.get_setting('config_icon_unchecked')
        self.RADIO_MARKED = utils.props.get_setting('config_icon_radio_checked')
        self.RADIO_UNMARKED = utils.props.get_setting('config_icon_radio_unchecked')
        self.EDIT_ICON = utils.props.get_setting('config_icon_edit')
        self.BACK_ICON = utils.props.get_setting('config_icon_back')
        self.LIST_ICON = utils.props.get_setting('config_icon_unnumbered_list')

        self.html = mw_html.MwHtmlAdv(html_id='mediawiker_configurator')
        self.set_css()
        self.show()

    def set_css(self):
        base_font_size = self.html.css_rules['body']['font-size']
        self.html.css_rules['a']['color'] = '#C5EFF7'
        self.html.css_rules['a']['text-decoration'] = 'none'
        self.html.css_rules['a']['font-size'] = self.html.get_font_size(base_font_size, 0.1)
        self.html.css_rules['ul']['padding-right'] = '2rem'
        self.html.css_rules['ul']['margin-left'] = '0.2rem'
        self.html.css_rules['li']['font-size'] = self.html.get_font_size(base_font_size, 0.1)
        self.html.css_rules['li']['margin-top'] = '0.2rem'
        self.html.css_rules['h1,h2,h3,h4']['margin'] = '2rem'
        self.html.css_rules['h1,h2,h3,h4']['color'] = 'white'
        self.html.css_rules['.undefined'] = {'padding': '5px', 'color': '#c0c0c0'}

    def post_prepare_popup(self, section, popup):
        if not section == 'Main':

            link = self.html.link(
                url=self.to_s({'section': 'BACK', 'value': 'BACK', 'params': '', 'goto': 'Main'}),
                text='Back'
            )
            status = self.icon(self.BACK_ICON)
            popup.append(self.html.li(link, icon=status['icon'], css_class=status['css_class']))
        return popup

    def append_toggle(self, popup, name, status, value, section, params, goto, adv=None):
        if adv is None:
            adv = ''

        link = self.html.link(
            url=self.to_s({'section': section, 'value': value, 'params': params, 'goto': goto}),
            text=name
        )

        popup.append(self.html.li('{}{}'.format(link, adv), icon=status['icon'], css_class=status['css_class']))
        return popup

    def icon(self, icon, css_class='success'):
        # return self.html.strong(icon, css_class)
        return {
            'icon': icon,
            'css_class': css_class
        }

    def pretty(self, value):
        return ' '.join(value.replace('mediawiker_', '').replace('mediawiki_', '').split('_')).capitalize()

    def prepare_popup_edit_panel(self, section, popup):

        popup.append(self.html.ul())

        popup = self.append_toggle(
            popup=popup,
            name='[All turn ON]',
            status=self.icon(self.MARKED, 'success'),
            value='all_on',
            section=section,
            params=0,
            goto=section
        )

        popup = self.append_toggle(
            popup=popup,
            name='[All turn OFF]',
            status=self.icon(self.UNMARKED, 'error'),
            value='all_off',
            section=section,
            params=0,
            goto=section
        )

        self.options_default = utils.props.get_default_setting('panel')
        self.options = utils.props.get_setting('panel')
        snippet_char = utils.props.get_setting('snippet_char')

        for idx, option in enumerate(self.options_default):
            option_value = True if option in self.options else False
            option_text = '{} {}'.format(snippet_char, option.get('caption')) if option.get('type') == 'snippet' else option.get('caption')
            popup = self.append_toggle(
                popup=popup,
                name=option_text,
                status=self.icon(
                    self.MARKED if option_value else self.UNMARKED,
                    'success' if option_value else 'error'
                ),
                value=not option_value,
                section=section,
                params=idx,
                goto=section
            )
        else:
            popup = self.post_prepare_popup(section, popup)
            popup.append(self.html.ul(close=True))

        return popup

    def show_main(self, section, popup):
        popup.append(self.html.h2('Mediawiker'))

        popup.append(self.html.ul())
        for option in self.MENU:
            link = self.html.link(
                url=self.to_s({'section': section, 'value': '', 'params': '', 'goto': option}),
                text=option
            )
            popup.append(self.html.li(link, icon='&nbsp;'))
        else:
            popup.append(self.html.ul(close=True))
        return popup

    def show_edit_panel(self, section, popup):
        popup.append(self.html.h2('Edit panel'))
        popup = self.prepare_popup_edit_panel(section=section, popup=popup)
        return popup

    def show_preferences(self, section, popup):
        popup.append(self.html.h2('Preferences'))

        popup.append(self.html.ul())
        for option in sorted(utils.props.props, key=lambda k: utils.props.props[k]['text'].lower()):
            value = utils.props.get_setting(option)
            name = utils.props.props.get(option)['text']
            option_default_value = utils.props.get_default_setting(option)
            if isinstance(option_default_value, bool):

                status = self.icon(
                    self.MARKED if value else self.UNMARKED,
                    'success' if value else 'error'
                )
                value = not value
                params = (option, bool.__name__)

            elif not isinstance(option_default_value, list) and not isinstance(option_default_value, dict):
                if isinstance(option_default_value, int):
                    value_pretty = self.html.code(value)
                    option_type = int.__name__
                else:
                    option_type = str.__name__
                    value_pretty = '"{}"'.format(self.html.code(value)) if value else '""'

                name = '{}: {}'.format(name, value_pretty)
                status = self.icon(self.LIST_ICON)
                params = (option, option_type)
            else:
                continue

            popup = self.append_toggle(
                popup=popup,
                name=name,
                status=status,
                value=value,
                section=section,
                params=params,
                goto=section
            )

        else:
            popup = self.post_prepare_popup(section, popup)
            popup.append(self.html.ul(close=True))
        return popup

    def show_select_wiki(self, section, popup):
        popup.append(self.html.h2('Select wiki'))
        sites = utils.props.get_setting('site')
        site_active = utils.get_view_site()

        popup.append(self.html.ul())

        # new
        popup = self.append_toggle(
            popup=popup,
            name='New',
            status=self.icon(self.RADIO_UNMARKED),
            value='edit',
            section=section,
            params='new',
            goto='Edit site/new'
        )

        for site in sorted(sites.keys(), key=str.lower):
            link = self.html.link(
                url=self.to_s({
                    'section': section,
                    'value': 'edit',
                    'params': site,
                    'goto': 'Edit site/{}'.format(site)
                }),
                text=self.html.span(self.icon(self.EDIT_ICON)['icon'], self.icon(self.EDIT_ICON)['css_class'])
            )
            adv = '&nbsp;&nbsp;{}'.format(link)
            popup = self.append_toggle(
                popup=popup,
                name=site,
                status=self.icon(
                    self.RADIO_MARKED if site == site_active else self.RADIO_UNMARKED,
                    'success' if site == site_active else 'error'
                ),
                value='',
                section=section,
                params=site,
                goto=section,
                adv=adv)
        else:
            popup = self.post_prepare_popup(section, popup)
            popup.append(self.html.ul(True))

        return popup

    def show_edit_site(self, section, popup):
        section_clear, site = section.split('/')
        popup.append(self.html.h2('Edit site: {}'.format(site)))

        if site == 'new':
            site = ''
            settings_default = {self.PROPERTY_SITE_NAME: utils.props.props_site[self.PROPERTY_SITE_NAME]}

        else:
            settings_default = utils.props.props_site

        popup.append(self.html.ul())
        for option in sorted(settings_default, key=lambda k: settings_default[k]['text'].lower()):
            option_pretty = utils.props.props_site[option]['text']
            value = utils.props.get_site_setting(site, option) if option != self.PROPERTY_SITE_NAME else site
            if utils.props.props_site[option]['type'] is bool:

                name = option_pretty
                status = self.icon(
                    self.MARKED if value else self.UNMARKED,
                    'success' if value else 'error'
                )
                value = not value
                params = (site, option, bool.__name__)

            else:
                if option.endswith(('password', 'secret', 'token')):
                    option_type = self.TYPE_PASSWORD
                    value_pretty = utils.props.get_setting('password_char') * 8 if value else '""'
                else:
                    option_type = str.__name__
                    value_pretty = '"{}"'.format(self.html.code(value)) if value else '""'

                name = '{}: {}'.format(option_pretty, value_pretty)
                status = self.icon(
                    self.LIST_ICON,
                    'success' if value else 'undefined'
                )
                params = (site, option, option_type)

            popup = self.append_toggle(
                popup=popup,
                name=name,
                status=status,
                value=value,
                section=section_clear,
                params=params,
                goto=section
            )

        else:
            popup = self.post_prepare_popup(section, popup)
            popup.append(self.html.ul(close=True))
        return popup

    def show_tab_options(self, section, popup):
        popup.append(self.html.h2('Tab options'))

        settings_default = utils.props.props_view

        popup.append(self.html.ul())

        for option in settings_default.keys():
            name = settings_default[option]['text']
            option_type = settings_default[option]['type']
            value = utils.props.get_view_setting(self.view, option)

            if option_type is bool:
                status = self.icon(self.MARKED if value else self.UNMARKED, 'success' if value else 'error')
                value = not value
            else:
                value_pretty = self.html.code(value) if value is not None else ''
                if option_type is str:
                    value_pretty = '"{}"'.format(value_pretty)
                name = '{}: {}'.format(name, value_pretty)
                status = self.icon(self.LIST_ICON)

            popup = self.append_toggle(
                popup=popup,
                name=name,
                status=status,
                value=value,
                section=section,
                params=(option, option_type.__name__),
                goto=section
            )

        else:
            popup = self.post_prepare_popup(section, popup)
            popup.append(self.html.ul(close=True))

        return popup

    def show(self, section='Main'):

        popup = []
        if section == 'Main':
            popup = self.show_main(section, popup)

        elif section == 'Edit panel':
            popup = self.show_edit_panel(section, popup)

        elif section == 'Preferences':
            popup = self.show_preferences(section, popup)

        elif section == 'Select wiki':
            popup = self.show_select_wiki(section, popup)

        elif section.startswith('Edit site'):
            popup = self.show_edit_site(section, popup)

        elif section == 'Tab options':
            popup = self.show_tab_options(section, popup)

        self.show_popup(popup)

    def show_popup(self, popup):
        if not popup:
            return

        # TODO: refact
        sh_line = self.view.lines(self.view.visible_region())[0]
        sh_point = sh_line.a + 20

        self.view.show_popup(
            content=self.html.build(popup),
            flags=0,
            location=sh_point,
            max_width=800,
            max_height=600,
            on_navigate=self.on_navigate,
            on_hide=None)

    def to_s(self, d):
        return json.dumps(d).replace('"', '&quot;')

    def to_d(self, s):
        return json.loads(s.replace('&quot;', '"'))

    def toggle_edit_panel(self, value, idx):
        elem = self.options_default[idx]
        if value == 'all_on':
            utils.props.del_setting('panel')
        else:
            if value == 'all_off':
                self.options = []
            elif value and elem not in self.options:
                self.options.append(elem)
            elif elem in self.options:
                self.options.remove(elem)
            utils.props.set_setting('panel', self.options)

    def on_navigate_edit_panel(self, section, value, params, goto):
        idx = int(params)
        self.toggle_edit_panel(value, idx)
        return False

    def on_navigate_preferences(self, section, value, params, goto):
        is_async = False
        option, option_type = params
        if option_type == bool.__name__:
            utils.props.set_setting(option, value)
        elif option_type in (str.__name__, int.__name__):
            is_async = True
            option_pretty = self.pretty(option)
            panel = InputValue(callback=self.show, option=option, goto=goto, option_type=option_type)
            panel.show_input(panel_title=option_pretty, value_pre=value)

        return is_async

    def on_navigate_select_wiki(self, section, value, params, goto):
        if value != 'edit':
            if utils.props.get_view_setting(self.view, 'is_here', False):
                utils.props.set_view_setting(self.view, 'site', params)
            utils.props.set_setting("site_active", params)

        return False

    def on_navigate_edit_site(self, section, value, params, goto):
        is_async = False
        site, option, option_type = params
        if option == self.PROPERTY_SITE_NAME:
            option_pretty = self.pretty(option)
            panel = InputSiteValue(callback=self.show, site=site, option=option, goto=goto)
            panel.show_input(panel_title=option_pretty, value_pre=value)
        elif option_type == bool.__name__:
            utils.props.set_site_setting(site, option, value)
        elif option_type in (str.__name__, self.TYPE_PASSWORD):
            is_async = True
            option_pretty = self.pretty(option)
            panel = InputSiteValue(callback=self.show, site=site, option=option, goto=goto)
            if option_type == str.__name__:
                panel.show_input(panel_title=option_pretty, value_pre=value)
            elif option_type == self.TYPE_PASSWORD:
                panel.show_input_passwd(value_pre=value)

        return is_async

    def on_navigate_tab_options(self, section, value, params, goto):
        is_async = False
        option, option_type = params
        if option_type == bool.__name__:
            utils.props.set_view_setting(self.view, option, value)
        elif option_type in (int.__name__, str.__name__):
            is_async = True
            option_pretty = self.pretty(option)
            panel = InputTabValue(callback=self.show, option=option, goto=goto, option_type=option_type)
            panel.show_input(panel_title=option_pretty, value_pre=str(value))

        return is_async

    def on_navigate(self, url):

        _ = self.to_d(url)
        section = _['section']
        value = _['value']
        params = _['params']
        goto = _['goto']

        is_async = False

        # Edit panel commands
        if section == 'Edit panel':

            is_async = self.on_navigate_edit_panel(section, value, params, goto)

        # Edit preferences
        elif section == 'Preferences':

            is_async = self.on_navigate_preferences(section, value, params, goto)

        # Select active site
        elif section == 'Select wiki':

            is_async = self.on_navigate_select_wiki(section, value, params, goto)

        # Edit site configuration
        elif section == 'Edit site':

            is_async = self.on_navigate_edit_site(section, value, params, goto)

        # Edit view options
        elif section == 'Tab options':

            is_async = self.on_navigate_tab_options(section, value, params, goto)

        if not is_async:
            self.show(goto)


class InputValue(utils.InputPanel):

    def __init__(self, callback, option, goto, option_type=str.__name__):
        super(InputValue, self).__init__(callback=callback)
        self.option = option
        self.goto = goto
        self.callback = callback
        self.option_type = option_type

    def on_done(self, value):
        self.value = int(value) if self.option_type == int.__name__ else value
        self.set_setting()

    def on_cancel(self):
        utils.set_timeout_async(self.callback(self.goto), 0)

    def set_setting(self):
        utils.props.set_setting(self.option, self.value)
        utils.set_timeout_async(self.callback(self.goto), 0)


class InputTabValue(InputValue):

    def set_setting(self):
        utils.props.set_view_setting(sublime.active_window().active_view(), self.option, self.value)
        utils.set_timeout_async(self.callback(self.goto), 0)


class InputSiteValue(utils.InputPanel):

    def __init__(self, callback, site, option, goto):
        super(InputSiteValue, self).__init__(callback=callback)
        self.site = site
        self.option = option
        self.goto = goto
        self.callback = callback
        self.ph = None

    def show_input(self, panel_title='Input', value_pre=''):
        self.value_pre = value_pre
        self.window.show_input_panel(panel_title, value_pre, self.on_done, self.on_change, self.on_cancel)

    def show_input_passwd(self, value_pre):
        self.ph = utils.PasswordHider()
        password = self.ph.hide(value_pre)
        self.show_input(panel_title='Password', value_pre=password)

    def on_change(self, str_val):
        if str_val is not None and self.ph:
            password = self.ph.hide(str_val)
            if password != str_val:
                self.show_input('Password:', password)

    def on_done(self, value):
        self.value = value if not self.ph else self.ph.done()
        self.set_setting()

    def on_cancel(self):
        utils.set_timeout_async(self.callback(self.goto), 0)

    def set_setting(self):
        if self.option == 'name':
            settings = utils.props.get_setting('site')
            if not self.value_pre or self.value_pre not in settings:
                settings[self.value] = {}
            else:
                settings[self.value] = dict(settings[self.value_pre])
                del settings[self.value_pre]
            section = self.goto.split('/')[0]
            self.goto = '/'.join([section, self.value])
            utils.props.set_setting('site', settings)
        else:
            utils.props.set_site_setting(self.site, self.option, self.value if self.value is not None else '')

        utils.set_timeout_async(self.callback(self.goto), 0)
