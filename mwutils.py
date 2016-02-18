#!/usr/bin/env python\n
# -*- coding: utf-8 -*-

import sys
pythonver = sys.version_info[0]

from os.path import splitext, basename
import re
import urllib

try:
    # Python 2.7+
    from collections import OrderedDict
except ImportError:
    # Python 2.6
    from ordereddict import OrderedDict

import sublime
import requests

if pythonver >= 3:
    # NOTE: load from package, not used now because custom ssl
    # current_dir = dirname(__file__)
    # if '.sublime-package' in current_dir:
    #     sys.path.append(current_dir)
    #     import mwclient
    # else:
    #     from . import mwclient
    from html.parser import HTMLParser
    from . import mwclient
else:
    from HTMLParser import HTMLParser
    import mwclient


def get_setting(key, default_value=None):
    settings = sublime.load_settings('Mediawiker.sublime-settings')
    return settings.get(key, default_value)


def set_setting(key, value):
    settings = sublime.load_settings('Mediawiker.sublime-settings')
    settings.set(key, value)
    sublime.save_settings('Mediawiker.sublime-settings')


def set_syntax(title=None):
    if title and title.startswith('Module:') and not title.find('/doc'):
        # Scribunto lua modules
        if int(sublime.version()) >= 3084:  # dev build, or 3103 in main
            syntax = 'Packages/Lua/Lua.sublime-syntax'
        else:
            syntax = 'Packages/Lua/Lua.tmLanguage'
    else:
        syntax = get_setting('mediawiki_syntax', 'Packages/Mediawiker/MediawikiNG.tmLanguage')
    sublime.active_window().active_view().set_syntax_file(syntax)


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


def get_connect(password=None):
    return mwcon.get_site(password)


# wiki related functions..
def get_page_text(site, title):
    denied_message = 'You have not rights to edit this page. Click OK button to view its source.'
    page = site.Pages[title]

    if page.can('edit'):
        sublime.active_window().active_view().settings().set('page_revision', page.revision)
        return True, page.text()
    else:
        if sublime.ok_cancel_dialog(denied_message):
            if page.can('read'):
                return False, page.text()
            else:
                return False, ''
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

class WikiConnect(object):

    conns = {}

    def _site_preinit(self):
        site_active = get_view_site()
        site_list = get_setting('mediawiki_site')
        self.site_params = site_list.get(site_active, {})
        self.site = self.site_params['host']

    def _site_init(self):
        self.path = self.site_params['path']
        self.username = self.site_params['username']
        self.password = self.site_params['password']
        self.domain = self.site_params['domain']
        self.proxy_host = self.site_params.get('proxy_host', '')
        self.http_auth_login = self.site_params.get('http_auth_login', '')
        self.http_auth_password = self.site_params.get('http_auth_password', '')
        self.is_https = self.site_params.get('https', False)
        self.is_ssl_cert_verify = self.site_params.get('is_ssl_cert_verify', True)
        self.host = self.site if not self.is_https else ('https', self.site)
        self.proxies = None
        if self.proxy_host:
            # proxy host like: http(s)://user:pass@10.10.1.10:3128
            # NOTE: PC uses requests ver. 2.7.0. Per-host proxies supported from 2.8.0 version only.
            # http://docs.python-requests.org/en/latest/community/updates/#id4
            # host_key = '%s://%s' % ('https' if self.is_https else 'http', self.site)
            # using proto only..
            host_key = 'https' if self.is_https else 'http'
            self.proxies = {
                host_key: self.proxy_host
            }

    def get_site(self, password=None):

        self._site_preinit()

        sitecon = self.conns.get(self.site, None)
        if sitecon:
            # print('return cached connection', sitecon)
            return sitecon

        self._site_init()

        if password is not None:
            self.password = password

        if self.is_https:
            sublime.status_message('Trying to get https connection to https://%s' % self.site)

        if self.proxy_host:
            sublime.status_message('Connection with proxy %s to %s' % (self.proxy_host, self.site))

        try:
            sitecon = mwclient.Site(host=self.host, path=self.path, verify=self.is_ssl_cert_verify, proxies=self.proxies)
        except requests.exceptions.HTTPError as e:
            is_use_http_auth = self.site_params.get('use_http_auth', False)
            if e.response.status_code == 401 and is_use_http_auth:
                http_auth_header = e.response.headers.get('www-authenticate', '')
                sitecon = self._http_auth(http_auth_header)
            else:
                sublime.message_dialog('HTTP connection failed: %s' % e[1])
                raise Exception('HTTP connection failed.')
        except Exception as e:
            sublime.message_dialog('Connection failed for %s: %s' % (self.host, e))
            raise Exception('HTTP connection failed: %s' % e)

        # if login is not empty - auth required
        if self.username:
            try:
                if sitecon is not None:
                    sitecon.login(username=self.username, password=self.password, domain=self.domain)
                    sublime.status_message('Logon successfully.')
                else:
                    sublime.status_message('Login failed: connection unavailable.')
            except mwclient.LoginError as exc:
                e = exc.args if pythonver >= 3 else exc
                sublime.status_message('Login failed: %s' % e[1]['result'])
                return
        else:
            sublime.status_message('Connection without authorization')

        if sitecon:
            self.conns[self.site] = sitecon

        return sitecon

    def _http_auth(self, http_auth_header):
        sitecon = None
        DIGEST_REALM = 'Digest realm'
        BASIC_REALM = 'Basic realm'

        if not self.http_auth_login or not self.http_auth_password:
            raise Exception('HTTP connection failed: Empty authorization data.')

        httpauth = None
        realm = None
        if http_auth_header.startswith(BASIC_REALM):
            realm = BASIC_REALM
        elif http_auth_header.startswith(DIGEST_REALM):
            realm = DIGEST_REALM

        if realm is not None:
            if realm == BASIC_REALM:
                httpauth = requests.auth.HTTPBasicAuth(self.http_auth_login, self.http_auth_password)
            elif realm == DIGEST_REALM:
                httpauth = requests.auth.HTTPDigestAuth(self.http_auth_login, self.http_auth_password)

            if httpauth:
                sitecon = mwclient.Site(host=self.host, path=self.path, httpauth=httpauth, verify=self.is_ssl_cert_verify, proxies=self.proxies)
        else:
            error_message = 'HTTP connection failed: Unknown realm.'
            sublime.status_message(error_message)
            raise Exception(error_message)
        return sitecon


class InputPanel(object):

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


class PasswordHider(object):

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


class WikiaInfoboxParser(HTMLParser):

    is_infobox = False
    TAG_INFOBOX = 'infobox'
    # TAG_FORMAT = 'format'
    TAG_DEFAULT = 'default'
    ATTR_SOURCE = 'source'

    tag_path = []
    params = None

    def handle_starttag(self, tag, attrs):
        if tag.lower() == self.TAG_INFOBOX:
            self.is_infobox = True
            self.params = OrderedDict()
        elif self.is_infobox:
            self.tag_path.append((tag, attrs))
            source = self.get_source(attrs)
            if source:
                self.params[source] = ''

    def handle_endtag(self, tag):
        self.tag_path = self.tag_path[:-1]
        if tag.lower() == self.TAG_INFOBOX:
            self.is_infobox = False

    def handle_data(self, data):
        val = data.strip()
        if self.is_infobox and val:
            tag_current = self.tag_path[-1][0]
            tag_parent_param, source = self.get_parent_param()
            if tag_parent_param and source:
                default_value = ''
                if tag_current == self.TAG_DEFAULT:
                    default_value = val
                self.params[source] = default_value

    def get_parent_param(self):
        for tag in reversed(self.tag_path):
            source = self.get_source(tag[1])
            if source:
                return tag, source
        return None, None

    def get_source(self, attrs):
        for attr in attrs:
            if attr[0].lower() == self.ATTR_SOURCE:
                return attr[1]
        return None

    def get_params_list(self):
        params_list = []
        if self.params:
            for par in self.params.keys():
                param = '%s=%s' % (par, self.params[par])
                params_list.append(param)
        return params_list


mwcon = WikiConnect()
