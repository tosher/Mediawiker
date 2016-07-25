#!/usr/bin/env python\n
# -*- coding: utf-8 -*-

import sys
pythonver = sys.version_info[0]
import sublime
import sublime_plugin
if pythonver >= 3:
    from . import mw_utils as mw
else:
    import mw_utils as mw


class MediawikerProcessSiteCommand(sublime_plugin.WindowCommand):

    site = None
    site_now = None
    site_name = None

    def _on_change_password(self, on_done, hint='Password:'):
        def password_hider(str_val):
            if str_val and self.is_hide_password:
                password = self.ph.hide(str_val)
                if password != str_val:
                    self.window.show_input_panel(hint, password, on_done, password_hider, None)
        return password_hider

    def run(self):
        self.is_hide_password = mw.get_setting('mediawiker_password_input_hide')
        self.hosts = mw.get_setting('mediawiki_site', {})
        self.window.show_input_panel('Internal site name:', '', self.get_host, None, None)

    def get_host(self, data):
        if data:
            self.site = {}
            self.site_now = {}
            self.site_name = data.strip()
            if self.site_name in self.hosts:
                self.site_now = self.hosts[self.site_name]
            self.window.show_input_panel('Host (en.wikipedia.org):', self.site_now.get('host', ''), self.get_https, None, None)

    def get_https(self, data):
        self.site['host'] = data
        message = 'Is https required for this host?'
        if self.site_now:
            message += '\nCurrent settings: %s' % ('Yes' if self.site_now.get('https', False) else 'No')
        self.site['https'] = True if sublime.ok_cancel_dialog(message, 'Yes') else False
        self.get_domain()

    def get_domain(self):
        self.window.show_input_panel('Domain (optional):', self.site_now.get('domain', ''), self.get_pagepath, None, None)

    def get_pagepath(self, data):
        self.site['domain'] = data
        self.window.show_input_panel('Page path [/wiki/]:', self.site_now.get('pagepath', ''), self.get_path, None, None)

    def get_path(self, data):
        self.site['pagepath'] = data if data else '/wiki/'
        self.window.show_input_panel('Api path [/w/]:', self.site_now.get('path', ''), self.get_username, None, None)

    def get_username(self, data):
        self.site['path'] = data if data else '/w/'
        self.window.show_input_panel('Username:', self.site_now.get('username', ''), self.get_password, None, None)

    def get_password(self, data):
        self.site['username'] = data

        hint = 'Password:'
        if self.is_hide_password:
            self.ph = mw.PasswordHider()
        on_done = self.get_proxy
        on_change = self._on_change_password(on_done=on_done, hint=hint)
        self.window.show_input_panel(hint, self.site_now.get('password', ''), on_done, on_change, None)

    def get_proxy(self, data):
        if self.is_hide_password:
            self.site['password'] = self.ph.done()
            del(self.ph)
        else:
            self.site['password'] = data

        self.window.show_input_panel('Proxy server (optional, host:port):', self.site_now.get('proxy_host', ''), self.get_httpauth, None, None)

    def get_httpauth(self, data):
        self.site['proxy_host'] = data
        message = 'Is http authorization required for this host?'
        if self.site_now:
            message += '\nCurrent settings: %s' % ('Yes' if self.site_now.get('use_http_auth', False) else 'No')
        self.site['use_http_auth'] = True if sublime.ok_cancel_dialog(message, 'Yes') else False

        if self.site['use_http_auth']:
            self.get_httpauth_login()
        else:
            self.site['http_auth_login'] = ''
            self.site['http_auth_password'] = ''
            self.setup_finish()

    def get_httpauth_login(self):
        self.window.show_input_panel('Http auth login:', self.site_now.get('http_auth_login', ''), self.get_httpauth_password, None, None)

    def get_httpauth_password(self, data):
        self.site['http_auth_login'] = data

        hint = 'Http auth password:'
        if self.is_hide_password:
            self.ph = mw.PasswordHider()
        on_done = self.get_httpauth_password_done
        on_change = self._on_change_password(on_done=on_done, hint=hint)
        self.window.show_input_panel(hint, self.site_now.get('http_auth_password', ''), on_done, on_change, None)

    def get_httpauth_password_done(self, data):
        if self.is_hide_password:
            self.site['http_auth_password'] = self.ph.done()
            del(self.ph)
        else:
            self.site['http_auth_password'] = data
        self.setup_finish()

    def setup_finish(self):
        self.hosts[self.site_name] = self.site
        mw.set_setting('mediawiki_site', self.hosts)

        if sublime.ok_cancel_dialog('Activate this host?'):
            mw.set_setting("mediawiki_site_active", self.site_name)

        sublime.status_message('Setup finished.')
