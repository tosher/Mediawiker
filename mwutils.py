#!/usr/bin/env python\n
# -*- coding: utf-8 -*-

import sys
pythonver = sys.version_info[0]

from os.path import splitext, basename
import re
import urllib
import base64
from hashlib import md5
import uuid

import sublime

if pythonver >= 3:
    # NOTE: load from package, not used now because custom ssl
    # current_dir = dirname(__file__)
    # if '.sublime-package' in current_dir:
    #     sys.path.append(current_dir)
    #     import mwclient
    # else:
    #     from . import mwclient

    from . import mwclient
else:
    import mwclient


def get_setting(key, default_value=None):
    settings = sublime.load_settings('Mediawiker.sublime-settings')
    return settings.get(key, default_value)


def set_setting(key, value):
    settings = sublime.load_settings('Mediawiker.sublime-settings')
    settings.set(key, value)
    sublime.save_settings('Mediawiker.sublime-settings')


def get_view_site():
    try:
        return sublime.active_window().active_view().settings().get('mediawiker_site', get_setting('mediawiki_site_active'))
    except:
        # st2 exception on start.. sublime not available on activated..
        return get_setting('mediawiki_site_active')


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

    # auth = 'username="%s", realm="%s", nonce="%s", uri="%s", response="%s", opaque="%s", qop="%s", nc=%s, cnonce="%s"' %
    # (username, realm, nonce, digest_uri, response, opaque, qop, nc, cnonce)
    auth_tpl = 'username="%s", realm="%s", nonce="%s", uri="%s", response="%s", qop="%s", nc=%s, cnonce="%s"'

    return auth_tpl % (username, realm, nonce, digest_uri, response, qop, nc, cnonce)


def http_auth(http_auth_header, host, path, login, password):
    sitecon = None
    DIGEST_REALM = 'Digest realm'
    BASIC_REALM = 'Basic realm'

    # http_auth_header = e[1].getheader('www-authenticate')
    custom_headers = {}
    realm = None
    if http_auth_header.startswith(BASIC_REALM):
        realm = BASIC_REALM
    elif http_auth_header.startswith(DIGEST_REALM):
        realm = DIGEST_REALM

    if realm is not None:
        if realm == BASIC_REALM:
            auth = deco(base64.standard_b64encode(enco('%s:%s' % (login, password))))
            custom_headers = {'Authorization': 'Basic %s' % auth}
        elif realm == DIGEST_REALM:
            auth = get_digest_header(http_auth_header, login, password, '%sapi.php' % path)
            custom_headers = {'Authorization': 'Digest %s' % auth}

        if custom_headers:
            sitecon = mwclient.Site(host=host, path=path, custom_headers=custom_headers)
    else:
        error_message = 'HTTP connection failed: Unknown realm.'
        sublime.status_message(error_message)
        raise Exception(error_message)
    return sitecon


def get_connect(password=None):
    # site_name_active = mw.get_setting('mediawiki_site_active')
    site_active = get_view_site()
    site_list = get_setting('mediawiki_site')
    site_params = site_list[site_active]
    site = site_params['host']
    path = site_params['path']
    username = site_params['username']
    if password is None:
        password = site_params['password']
    domain = site_params['domain']
    proxy_host = site_params.get('proxy_host', '')
    is_https = site_params.get('https', False)
    if is_https:
        sublime.status_message('Trying to get https connection to https://%s' % site)
    host = site if not is_https else ('https', site)
    if proxy_host:
        # proxy_host format is host:port, if only host defined, 80 will be used
        host = proxy_host if not is_https else ('https', proxy_host)
        proto = 'https' if is_https else 'http'
        path = '%s://%s%s' % (proto, site, path)
        sublime.message_dialog('Connection with proxy: %s %s' % (host, path))

    try:
        sitecon = mwclient.Site(host=host, path=path)
    except mwclient.HTTPStatusError as exc:
        e = exc.args if pythonver >= 3 else exc
        is_use_http_auth = site_params.get('use_http_auth', False)
        http_auth_login = site_params.get('http_auth_login', '')
        http_auth_password = site_params.get('http_auth_password', '')
        if e[0] == 401 and is_use_http_auth and http_auth_login:
            http_auth_header = e[1].getheader('www-authenticate')
            sitecon = http_auth(http_auth_header, host, path, http_auth_login, http_auth_password)
        else:
            sublime.status_message('HTTP connection failed: %s' % e[1])
            raise Exception('HTTP connection failed.')

    # if login is not empty - auth required
    if username:
        try:
            if sitecon is not None:
                sitecon.login(username=username, password=password, domain=domain)
                sublime.status_message('Logon successfully.')
            else:
                sublime.status_message('Login failed: connection unavailable.')
        except mwclient.LoginError as e:
            sublime.status_message('Login failed: %s' % e[1]['result'])
            return
    else:
        sublime.status_message('Connection without authorization')
    return sitecon

# wiki related functions..


def get_page_text(site, title):
    denied_message = 'You have not rights to edit this page. Click OK button to view its source.'
    page = site.Pages[title]
    if page.can('edit'):
        return True, page.edit()
    else:
        if sublime.ok_cancel_dialog(denied_message):
            return False, page.edit()
        else:
            return False, ''


def save_mypages(title, storage_name='mediawiker_pagelist'):

    title = title.replace('_', ' ')  # for wiki '_' and ' ' are equal in page name
    pagelist_maxsize = get_setting('mediawiker_pagelist_maxsize')
    # site_active = mw.get_setting('mediawiki_site_active')
    site_active = get_view_site()
    mediawiker_pagelist = get_setting(storage_name, {})

    if site_active not in mediawiker_pagelist:
        mediawiker_pagelist[site_active] = []

    my_pages = mediawiker_pagelist[site_active]

    if my_pages:
        while len(my_pages) >= pagelist_maxsize:
            my_pages.pop(0)

        if title in my_pages:
            # for sorting
            my_pages.remove(title)
    my_pages.append(title)
    set_setting(storage_name, mediawiker_pagelist)


def get_hlevel(header_string, substring):
    return int(header_string.count(substring) / 2)


def get_category(category_full_name):
    ''' From full category name like "Category:Name" return tuple (Category, Name) '''
    if ':' in category_full_name:
        return category_full_name.split(':')
    else:
        return 'Category', category_full_name


def get_page_url(page_name=''):
    # site_active = mw.get_setting('mediawiki_site_active')
    site_active = get_view_site()
    site_list = get_setting('mediawiki_site')
    site = site_list[site_active]["host"]

    is_https = False
    if 'https' in site_list[site_active]:
        is_https = site_list[site_active]["https"]

    proto = 'https' if is_https else 'http'
    pagepath = site_list[site_active]["pagepath"]
    if not page_name:
        page_name = strquote(get_title())
    if page_name:
        return '%s://%s%s%s' % (proto, site, pagepath, page_name)
    else:
        return ''


# classes..

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
