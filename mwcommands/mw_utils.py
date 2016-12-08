#!/usr/bin/env python\n
# -*- coding: utf-8 -*-

import sys

from os.path import splitext, basename
import re
import urllib.parse

try:
    # Python 2.7+
    from collections import OrderedDict
except ImportError:
    # Python 2.6
    from ordereddict import OrderedDict

import sublime
# import sublime_plugin
import requests

pythonver = sys.version_info[0]
if pythonver >= 3:
    # NOTE: load from package, not used now because custom ssl
    # current_dir = dirname(__file__)
    # if '.sublime-package' in current_dir:
    #     sys.path.append(current_dir)
    #     import mwclient
    # else:
    #     from . import mwclient
    from html.parser import HTMLParser
    from ..lib import mwclient
    from ..lib import browser_cookie3
else:
    from HTMLParser import HTMLParser
    from lib import mwclient


CATEGORY_NAMESPACE = 14  # category namespace number
IMAGE_NAMESPACE = 6  # file/image namespace number
TEMPLATE_NAMESPACE = 10  # template namespace number
SCRIBUNTO_NAMESPACE = 828  # scribunto module namespace number

COMMENT_REGIONS_KEY = 'comment'

PAGE_CANNOT_READ_MESSAGE = 'You have not rights to read/edit this page.'
PAGE_CANNOT_EDIT_MESSAGE = 'You have not rights to edit this page.'

NAMESPACE_SPLITTER = u':'
INTERNAL_LINK_SPLITTER = u'|'


def get_setting(key, default_value=None):
    settings = sublime.load_settings('Mediawiker.sublime-settings')
    return settings.get(key, default_value)


def set_setting(key, value):
    settings = sublime.load_settings('Mediawiker.sublime-settings')
    settings.set(key, value)
    sublime.save_settings('Mediawiker.sublime-settings')


def del_setting(key):
    settings = sublime.load_settings('Mediawiker.sublime-settings')
    settings.erase(key)
    sublime.save_settings('Mediawiker.sublime-settings')


def get_default_setting(key, default_value=None):
    settings = sublime.decode_value(sublime.load_resource('Packages/Mediawiker/Mediawiker.sublime-settings'))
    return settings.get(key, default_value)


def set_syntax(page_name=None, page_namespace=None):
    syntax = get_setting('mediawiki_syntax', 'Packages/Mediawiker/MediawikiNG.tmLanguage')

    if page_name and page_namespace:
        syntax_ext = 'sublime-syntax' if int(sublime.version()) >= 3084 else 'tmLanguage'

        # Scribunto lua modules, except doc subpage
        if page_namespace == SCRIBUNTO_NAMESPACE and not page_name.lower().endswith('/doc'):
            syntax = 'Packages/Lua/Lua.%s' % syntax_ext
        elif page_name.lower().endswith('.css'):
            syntax = 'Packages/CSS/CSS.%s' % syntax_ext
        elif page_name.endswith('.js'):
            syntax = 'Packages/Javascript/Javascript.%s' % syntax_ext

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
        return urllib.unquote(string_value.encode('utf-8')).decode('utf-8')


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
                status_message('Unauthorized file extension for mediawiki publishing. Check your configuration for correct extensions.')
                return ''
    return ''


def pagename_clear(pagename):
    """ Return clear pagename if page-url was set instead of.."""
    site_active = get_view_site()
    site_list = get_setting('mediawiki_site')
    site = site_list.get(site_active, {}).get('host', None)

    if not site:
        return pagename

    pagepath = site_list.get(site_active, {}).get('pagepath', None)
    if not pagepath:
        return pagename

    try:
        pagename = strunquote(pagename)
    except UnicodeEncodeError:
        pass
    except Exception:
        pass

    if site in pagename:
        pagename = re.sub(r'(https?://)?%s%s' % (site, pagepath), '', pagename)

    return pagename


def save_mypages(title, storage_name='mediawiker_pagelist'):

    title = title.replace('_', ' ')  # for wiki '_' and ' ' are equal in page name
    pagelist_maxsize = get_setting('mediawiker_pagelist_maxsize')
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


def get_internal_links_regions(view):

    def get_header(region):
        return strunquote(re.sub(pattern, r'\1', view.substr(region)))

    pattern = r'\[{2}(.*?)(\|.*?)?\]{2}'
    regions = view.find_all(pattern)
    return [(get_header(r), r) for r in regions]


def status_message(message, replace=None, is_panel=None):

    def status_message_sublime(message, replace=None):
        if replace:
            for r in replace:
                message = message.replace(r, '')
        sublime.status_message(message)

    is_use_message_panel = is_panel if is_panel is not None else get_setting('use_status_messages_panel', True)

    if is_use_message_panel:
        panel_name = 'mediawiker_panel'
        if int(sublime.version()) >= 3000:
            panel = sublime.active_window().find_output_panel(panel_name)

            if panel is None:
                panel = sublime.active_window().create_output_panel(panel_name)

            if panel is not None:
                # https://forum.sublimetext.com/t/style-the-output-panel/10316/6
                panel.set_syntax_file(get_setting('mediawiki_syntax', 'Packages/Mediawiker/MediawikiPanel.sublime-syntax'))
        else:
            panel = sublime.active_window().get_output_panel(panel_name)
            if panel is not None:
                panel.set_syntax_file(get_setting('mediawiki_syntax', 'Packages/Mediawiker/MediawikiNG_ST2.tmLanguage'))

        if panel is not None:
            sublime.active_window().run_command("show_panel", {"panel": "output.%s" % panel_name})
            panel.set_read_only(False)
            panel.run_command('mediawiker_insert_text', {'position': panel.size(), 'text': '%s\n' % message})
            panel.set_read_only(True)
            panel.show(panel.size())

        else:
            status_message_sublime(message, replace)
    else:
        status_message_sublime(message, replace)


def set_timeout_async(callback, delay):
    if pythonver >= 3000:
        sublime.set_timeout_async(callback, delay)
    else:
        sublime.set_timeout(callback, delay)


# classes..
class ConnectionFailed(Exception):
    pass


class PreAPI(object):

    def __init__(self, conman):
        self.conman = conman

    def get_connect(self):
        sitecon = self.conman.get_site()
        if not sitecon:
            raise ConnectionFailed("No valid connection available")
        return sitecon

    def call(self, func, **kwargs):

        if not isinstance(func, str):
            status_message('Error: PreAPI call arg must be a string.')
            return

        try:
            funcobj = getattr(self, func)
        except AttributeError as e:
            status_message('PreAPI %s error: %s' % (type(e).__name__, e))
            return

        if funcobj:
            while True:
                try:
                    return funcobj(**kwargs)
                except mwclient.errors.APIError as e:
                    status_message("%s exception: %s, trying to reconnect.." % (type(e).__name__, e))
                    try:
                        _ = self.get_connect(force=True)  # one time try to reconnect
                        if _:
                            return funcobj(**kwargs)
                        else:
                            status_message('Failed to call %s' % funcobj.__name__)  # TODO: check
                            break
                    except Exception as e:
                        status_message("%s exception: %s" % (type(e).__name__, e))
                        break
                except Exception as e:
                    status_message("%s exception: %s" % (type(e).__name__, e))
                    break

    def get_page(self, title):
        sitecon = self.get_connect()
        return sitecon.Pages.get(title, None)

    def get_page_backlinks(self, page, limit):
        return page.backlinks(limit=limit)

    def get_page_embeddedin(self, page, limit):
        return page.embeddedin(limit=limit)

    def get_page_langlinks(self, page):
        return page.langlinks()

    def save_page(self, page, text, summary, mark_as_minor):
        page.save(text, summary=summary.strip(), minor=mark_as_minor)

    def page_attr(self, page, attr_name):
        try:

            if attr_name == 'namespace_name':
                return getattr(page, 'name').split(':')[0]

            return getattr(page, attr_name)

        except AttributeError as e:
            status_message('%s exception: %s' % (type(e).__name__, e))

    def page_can_read(self, page):
        return page.can('read')

    def page_can_edit(self, page):
        return page.can('edit')

    def page_get_text(self, page):
        try:
            if self.page_can_read(page):
                return page.text()
        except:
            pass
        return ''

    def get_subcategories(self, category_root):
        sitecon = self.get_connect()
        return sitecon.Categories.get(category_root, [])

    def get_pages(self, prefix, namespace):
        sitecon = self.get_connect()
        return sitecon.allpages(prefix=prefix, namespace=namespace)

    def get_notifications(self):
        sitecon = self.get_connect()
        return sitecon.notifications()

    def get_parse_result(self, text, title):
        sitecon = self.get_connect()
        return sitecon.parse(text=text, title=title, disableeditsection=True).get('text', {}).get('*', '')

    def get_search_result(self, search, limit, namespace):
        sitecon = self.get_connect()
        return sitecon.search(search=search, what='text', limit=limit, namespace=namespace)

    def process_upload(self, file_handler, filename, description):
        # TODO: retest
        sitecon = self.get_connect()
        return sitecon.upload(file_handler, filename, description)

    def get_namespace_number(self, name):
        sitecon = self.get_connect()
        return sitecon.namespaces_canonical_invert.get(
            name, sitecon.namespaces_invert.get(
                name, sitecon.namespaces_aliases_invert.get(
                    name, None)))

    def image_init(self, name, extra_properties):
        sitecon = self.get_connect()
        return mwclient.Image(site=sitecon, name=name, extra_properties=extra_properties)

    def is_equal_ns(self, ns_name1, ns_name2):
        ns_name1_number = self.get_namespace_number(name=ns_name1)
        ns_name2_number = self.get_namespace_number(name=ns_name2)
        if ns_name1_number and ns_name2_number and int(ns_name1_number) == int(ns_name2_number):
            return True
        return False


class WikiConnect(object):

    conns = {}
    cj = None  # cookies
    username = ''
    password = ''
    AUTH_TYPE_LOGIN = 'login'
    AUTH_TYPE_OAUTH = 'oauth'
    AUTH_TYPE_COOKIES = 'cookies'

    def _site_preinit(self):
        site_active = get_view_site()
        site_list = get_setting('mediawiki_site')
        self.site_params = site_list.get(site_active, {})
        self.site = self.site_params.get('host', None)
        if not self.site:
            sublime.message_dialog('Host is not defined for site %s' % site_active)
        self.auth_type = self.site_params.get('authorization_type', self.AUTH_TYPE_LOGIN)
        self.cookies_browser = self.site_params.get('cookies_browser', 'chrome') if self.auth_type == self.AUTH_TYPE_COOKIES else None

    def try_cookie(self):
        if self.auth_type != self.AUTH_TYPE_COOKIES:
            return None

        cookie_files = get_setting('mediawiker_%s_cookie_files' % self.cookies_browser, [])
        if not cookie_files:
            cookie_files = None

        if self.cookies_browser == "firefox":
            return browser_cookie3.firefox(cookie_files=cookie_files, domain_name=self.site)
        elif self.cookies_browser == 'chrome':
            return browser_cookie3.chrome(cookie_files=cookie_files, domain_name=self.site)
        else:
            sublime.message_dialog("Incompatible browser for cookie: %s" % (self.cookies_browser or "Not defined"))

        return None

    def is_eq_cookies(self, cj1, cj2):
        cj1_set = set((c.domain, c.path, c.name, c.value) for c in cj1) if cj1 else set()
        cj2_set = set((c.domain, c.path, c.name, c.value) for c in cj2) if cj2 else set()
        return not bool(cj1_set - cj2_set or cj2_set - cj1_set)

    def _site_init(self):
        self.path = self.site_params.get('path', '/w/')
        self.username = self.site_params.get('username', '')
        self.password = self.site_params.get('password', '') if not self.password else self.password
        self.domain = self.site_params.get('domain', '')
        self.proxy_host = self.site_params.get('proxy_host', '')
        self.http_auth_login = self.site_params.get('http_auth_login', '')
        self.http_auth_password = self.site_params.get('http_auth_password', '')
        self.is_https = self.site_params.get('https', True)
        self.is_ssl_cert_verify = self.site_params.get('is_ssl_cert_verify', True)
        http_proto = 'https' if self.is_https else 'http'
        self.host = (http_proto, self.site)
        self.proxies = None
        # oauth params
        self.oauth_consumer_token = self.site_params.get('oauth_consumer_token', None)
        self.oauth_consumer_secret = self.site_params.get('oauth_consumer_secret', None)
        self.oauth_access_token = self.site_params.get('oauth_access_token', None)
        self.oauth_access_secret = self.site_params.get('oauth_access_secret', None)
        self.retry_timeout = self.site_params.get('retry_timeout', 30)

        if self.proxy_host:
            # proxy host like: http(s)://user:pass@10.10.1.10:3128
            # NOTE: PC uses requests ver. 2.7.0. Per-host proxies supported from 2.8.0 version only.
            # http://docs.python-requests.org/en/latest/community/updates/#id4
            # host_key = '%s://%s' % ('https' if self.is_https else 'http', self.site)
            # using proto only..
            self.proxies = {
                http_proto: self.proxy_host
            }

        self.requests_config = {
            'verify': self.is_ssl_cert_verify,
            'proxies': self.proxies,
            'timeout': (self.retry_timeout, None)
        }

    def set_password(self, password):
        if password:
            self.password = password

    def require_password(self):
        if self.AUTH_TYPE_LOGIN and not self.password:
            return True
        return False

    def url(self):
        return ''.join([self.host[0], '://', self.host[1]])

    def get_site(self, force=False):

        self._site_preinit()

        cj = self.try_cookie() if self.auth_type == self.AUTH_TYPE_COOKIES else None

        if self.auth_type == self.AUTH_TYPE_COOKIES and not self.is_eq_cookies(self.cj, cj):
            self.cj = cj
        elif not force and (self.auth_type != self.AUTH_TYPE_LOGIN or not self.username or self.password):
            sitecon = self.conns.get(self.site, None)
            if sitecon:
                return sitecon

        return self.get_new_connection()

    def get_new_connection(self):
        self._site_init()

        if self.proxy_host:
            status_message('Connection with proxy %s to %s..' % (self.proxy_host, self.url()))
        else:
            status_message('Connecting to %s..' % self.url())

        # oauth authorization
        if self.auth_type == self.AUTH_TYPE_OAUTH and all([self.oauth_consumer_token, self.oauth_consumer_secret, self.oauth_access_token, self.oauth_access_secret]):
            try:
                sitecon = mwclient.Site(host=self.host, path=self.path,
                                        retry_timeout=None,
                                        max_retries=None,
                                        consumer_token=self.oauth_consumer_token,
                                        consumer_secret=self.oauth_consumer_secret,
                                        access_token=self.oauth_access_token,
                                        access_secret=self.oauth_access_secret,
                                        requests=self.requests_config)
            except mwclient.OAuthAuthorizationError as exc:
                e = exc.args if pythonver >= 3 else exc
                status_message('Login failed: %s' % e[1])
                return
        else:

            # Site connection
            try:
                sitecon = mwclient.Site(host=self.host, path=self.path,
                                        retry_timeout=None,
                                        max_retries=None,
                                        requests=self.requests_config)
            except requests.exceptions.HTTPError as e:
                is_use_http_auth = self.site_params.get('use_http_auth', False)
                # additional http auth (basic, digest)
                if e.response.status_code == 401 and is_use_http_auth:
                    http_auth_header = e.response.headers.get('www-authenticate', '')
                    sitecon = self._http_auth(http_auth_header)
                else:
                    sublime.message_dialog('HTTP connection failed: %s' % e[1])
                    return
            except Exception as e:
                sublime.message_dialog('Connection failed for %s: %s' % (self.host, e))
                return

        if sitecon:
            status_message('Connection done.')
            status_message('Login in with type %s..' % self.auth_type)
            success_message = 'Login successfully.'
            # Cookie auth
            if self.auth_type == self.AUTH_TYPE_COOKIES and self.cj:
                try:
                    sitecon.login(cookies=self.cj, domain=self.domain)
                except mwclient.LoginError as exc:
                    e = exc.args if pythonver >= 3 else exc
                    status_message('Login failed: %s' % e[1]['result'])
                    return
            # Login/Password auth
            elif self.auth_type == self.AUTH_TYPE_LOGIN and self.username and self.password:
                try:
                    sitecon.login(username=self.username, password=self.password, domain=self.domain)
                except mwclient.LoginError as exc:
                    e = exc.args if pythonver >= 3 else exc
                    status_message('Login failed: %s' % e[1]['result'])
                    return
            # elif self.auth_type == self.AUTH_TYPE_OAUTH:
            else:
                success_message = 'Connection was made without authorization.'

            status_message(success_message)

            self.conns[self.site] = sitecon
            return sitecon

        return None

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
                sitecon = mwclient.Site(
                    host=self.host, path=self.path,
                    httpauth=httpauth,
                    requests=self.requests_config)
        else:
            error_message = 'HTTP connection failed: Unknown realm.'
            status_message(error_message)
            raise Exception(error_message)
        return sitecon


class InputPanel(object):

    def __init__(self, callback=None):
        self.callback = callback
        self.window = sublime.active_window()

    def show_input(self, panel_title='Input', value_pre=''):
        self.window.show_input_panel(panel_title, value_pre, self.on_done, self.on_change, self.on_cancel)

    def on_done(self, value):
        pass

    def on_change(self, value):
        pass

    def on_cancel(self, value=None):
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

    def on_done(self, title):
        set_timeout_async(self.callback(title), 0)


class InputPanelPassword(InputPanel):

    ph = None
    is_hide_password = False

    def get_password(self):
        site_active = get_view_site()
        site_list = get_setting('mediawiki_site')

        if site_list.get(site_active, {}).get('authorization_type', 'login') != 'login':
            self.on_done(password=None)
            return

        password = site_list.get(site_active, {}).get('password', '') or mwcon.password
        if site_list.get(site_active, {}).get("username", ''):
            # auth required if username exists in settings
            if not password:
                self.is_hide_password = get_setting('mediawiker_password_input_hide')
                if self.is_hide_password:
                    self.ph = PasswordHider()
                self.show_input('Password:', '')
            else:
                # return password
                self.on_done(password=None)
        else:
            # auth is not required
            self.on_done('')

    def on_change(self, str_val):
        if str_val is not None and self.is_hide_password and self.ph:
            password = self.ph.hide(str_val)
            if password != str_val:
                self.show_input('Password:', password)

    def on_done(self, password):
        if password and self.is_hide_password and self.ph:
            password = self.ph.done()
        if password:
            mwcon.set_password(password)
        set_timeout_async(self.callback, 0)


class PasswordHider(object):

    password = ''

    def hide(self, password):
        password_char = get_setting('mediawiker_password_char', '*')
        if len(password) < len(self.password):
            self.password = self.password[:len(password)]
        else:
            try:
                self.password = '%s%s' % (self.password, password.replace(password_char, ''))
            except:
                pass
        return password_char * len(self.password)

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
api = PreAPI(conman=mwcon)
