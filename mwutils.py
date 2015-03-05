#!/usr/bin/env python\n
# -*- coding: utf-8 -*-

import sys
pythonver = sys.version_info[0]

from os.path import splitext, basename
import re
import urllib
from hashlib import md5
import uuid

import sublime


def get_setting(key, default_value=None):
    settings = sublime.load_settings('Mediawiker.sublime-settings')
    return settings.get(key, default_value)


def set_setting(key, value):
    settings = sublime.load_settings('Mediawiker.sublime-settings')
    settings.set(key, value)
    sublime.save_settings('Mediawiker.sublime-settings')


def get_view_site():
    return sublime.active_window().active_view().settings().get('mediawiker_site', get_setting('mediawiki_site_active'))


def enco(value):
    ''' for md5 hashing string must be encoded '''
    if pythonver >= 3:
        return value.encode('utf-8')
    return value


def deco(value):
    ''' for py3 decode from bytes '''
    if pythonver >= 3:
        return value.decode('utf-8')
    return value


def strunquote(string_value):
    if pythonver >= 3:
        return urllib.parse.unquote(string_value)
    else:
        return urllib.unquote(string_value.encode('ascii')).decode('utf-8')


def strquote(string_value):
    if pythonver >= 3:
        return urllib.parse.quote(string_value)
    else:
        return urllib.quote(string_value.encode('utf-8'))


def get_title():
    ''' returns page title of active tab from view_name or from file_name'''

    view_name = sublime.active_window().active_view().name()
    if view_name:
        return view_name
    else:
        # haven't view.name, try to get from view.file_name (without extension)
        file_name = sublime.active_window().active_view().file_name()
        if file_name:
            wiki_extensions = get_setting('mediawiker_files_extension')
            title, ext = splitext(basename(file_name))
            if ext[1:] in wiki_extensions and title:
                return title
            else:
                sublime.status_message('Unauthorized file extension for mediawiki publishing. Check your configuration for correct extensions.')
                return ''
    return ''


def pagename_clear(pagename):
    """ Return clear pagename if page-url was set instead of.."""
    # site_active = get_setting('mediawiki_site_active')
    site_active = get_view_site()
    site_list = get_setting('mediawiki_site')
    site = site_list[site_active]['host']
    pagepath = site_list[site_active]['pagepath']
    try:
        pagename = strunquote(pagename)
    except UnicodeEncodeError:
        pass
    except Exception:
        pass

    if site in pagename:
        pagename = re.sub(r'(https?://)?%s%s' % (site, pagepath), '', pagename)

    sublime.status_message('Page name was cleared.')
    return pagename


def get_digest_header(header, username, password, path):
    HEADER_ATTR_PATTERN = r'([\w\s]+)=\"?([^".]*)\"?'
    METHOD = "POST"
    header_attrs = {}
    hprms = header.split(', ')
    for hprm in hprms:
        params = re.findall(HEADER_ATTR_PATTERN, hprm)
        for param in params:
            header_attrs[param[0]] = param[1]

    cnonce = str(uuid.uuid4())  # random clients string..
    nc = '00000001'
    realm = header_attrs['Digest realm']
    nonce = header_attrs['nonce']
    qop = header_attrs.get('qop', 'auth')
    digest_uri = header_attrs.get('uri', path)
    algorithm = header_attrs.get('algorithm', 'MD5')
    # TODO: ?
    # opaque = header_attrs.get('opaque', '')
    entity_body = ''  # TODO: ?

    if algorithm == 'MD5':
        ha1 = md5(enco('%s:%s:%s' % (username, realm, password))).hexdigest()
    elif algorithm == 'MD5-Sess':
        ha1 = md5(enco('%s:%s:%s' % (md5(enco('%s:%s:%s' % (username, realm, password))), nonce, cnonce))).hexdigest()

    if 'auth-int' in qop:
        ha2 = md5(enco('%s:%s:%s' % (METHOD, digest_uri, md5(entity_body)))).hexdigest()
    elif 'auth' in qop:
        ha2 = md5(enco('%s:%s' % (METHOD, digest_uri))).hexdigest()

    if 'auth' in qop or 'auth-int' in qop:
        response = md5(enco('%s:%s:%s:%s:%s:%s' % (ha1, nonce, nc, cnonce, qop, ha2))).hexdigest()
    else:
        response = md5(enco('%s:%s:%s' % (ha1, nonce, ha2))).hexdigest()

    # auth = 'username="%s", realm="%s", nonce="%s", uri="%s", response="%s", opaque="%s", qop="%s", nc=%s, cnonce="%s"' % (username, realm, nonce, digest_uri, response, opaque, qop, nc, cnonce)
    auth = 'username="%s", realm="%s", nonce="%s", uri="%s", response="%s", qop="%s", nc=%s, cnonce="%s"' % (username, realm, nonce, digest_uri, response, qop, nc, cnonce)
    return auth


class InputPanel:

    def __init__(self):
        self.window = sublime.active_window()

    def show_input(self, panel_title='Input', value_pre=''):
        self.window.show_input_panel(panel_title, value_pre, self.on_done, self.on_change, None)

    def on_done(self, value):
        pass

    def on_change(self, value):
        pass


class InputPanelPageTitle(InputPanel):

    def get_title(self, title):
        if not title:
            title_pre = ''
            # use clipboard or selected text for page name
            if bool(get_setting('mediawiker_clipboard_as_defaultpagename')):
                title_pre = sublime.get_clipboard().strip()
            if not title_pre:
                selection = self.window.active_view().sel()
                title_pre = self.window.active_view().substr(selection[0]).strip()
            self.show_input('Wiki page name:', title_pre)
        else:
            self.on_done(title)

    def on_change(self, title):
        if title:
            pagename_cleared = pagename_clear(title)
            if title != pagename_cleared:
                self.window.show_input_panel('Wiki page name:', pagename_cleared, self.on_done, self.on_change, None)


class InputPanelPassword(InputPanel):

    ph = None
    is_hide_password = False

    def get_password(self):
        # site_active = mw.get_setting('mediawiki_site_active')
        site_active = get_view_site()
        site_list = get_setting('mediawiki_site')
        password = site_list[site_active]["password"]
        if site_list[site_active]["username"]:
            # auth required if username exists in settings
            if not password:
                self.is_hide_password = get_setting('mediawiker_password_input_hide')
                if self.is_hide_password:
                    self.ph = PasswordHider()
                # need to ask for password
                # window.show_input_panel('Password:', '', self.on_done, self.on_change, None)
                self.show_input('Password:', '')
            else:
                # return password
                self.on_done(password)
        else:
            # auth is not required
            self.on_done('')

    def on_change(self, str_val):
        if str_val and self.is_hide_password and self.ph:
            password = self.ph.hide(str_val)
            if password != str_val:
                # self.window.show_input_panel('Password:', password, self.on_done, self.on_change, None)
                self.show_input('Password:', password)

    def on_done(self, password):
        if password and self.is_hide_password and self.ph:
            password = self.ph.done()
        self.command_run(password)  # defined in executor


class PasswordHider():

    password = ''
    PASSWORD_CHAR = u'\u25CF'

    def hide(self, password):
        if len(password) < len(self.password):
            self.password = self.password[:len(password)]
        else:
            try:
                self.password = '%s%s' % (self.password, password.replace(self.PASSWORD_CHAR, ''))
            except:
                pass
        return self.PASSWORD_CHAR * len(self.password)

    def done(self):
        try:
            return self.password
        except:
            pass
        finally:
            self.password = ''
