#!/usr/bin/env python\n
# -*- coding: utf-8 -*-

import sys
from os.path import splitext, basename, dirname, join
import imp
pythonver = sys.version_info[0]

import webbrowser
import urllib
import re
import sublime
import sublime_plugin
import base64
from hashlib import md5
import uuid

#https://github.com/wbond/sublime_package_control/wiki/Sublime-Text-3-Compatible-Packages
#http://www.sublimetext.com/docs/2/api_reference.html
#http://www.sublimetext.com/docs/3/api_reference.html
#sublime.message_dialog

st_version = 2
if int(sublime.version()) > 3000:
    st_version = 3

# import custom ssl module on linux
# thnx to wbond and his SFTP module!
# http://sublimetext.userecho.com/topic/50801-bundle-python-ssl-module/

arch_lib_path = None
if sublime.platform() == 'linux':
    arch_lib_path = join(dirname(__file__), 'lib', 'st%d_linux_%s' % (st_version, sublime.arch()))
    print('Mediawiker: enabling custom linux ssl module')
    for ssl_ver in ['1.0.0', '10', '0.9.8']:
        lib_path = join(arch_lib_path, 'libssl-' + ssl_ver)
        sys.path.append(lib_path)
        try:
            import _ssl
            print('Mediawiker: successfully loaded _ssl module for libssl.so.%s' % ssl_ver)
            break
        except (ImportError) as e:
            print('Mediawiker: _ssl module import error - ' + str(e))
    if '_ssl' in sys.modules:
        try:
            if sys.version_info < (3,):
                plat_lib_path = join(sublime.packages_path(), 'Mediawiker', 'lib', 'st2_linux')
                m_info = imp.find_module('ssl', [plat_lib_path])
                m = imp.load_module('ssl', *m_info)
            else:
                import ssl
                print('Mediawiker: ssl loaded!')
        except (ImportError) as e:
            print('Mediawiker: ssl module import error - ' + str(e))

# after ssl mwclient import
# in httpmw.py http_compat will be reloaded
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

CATEGORY_NAMESPACE = 14  # category namespace number
IMAGE_NAMESPACE = 6  # image namespace number
TEMPLATE_NAMESPACE = 10  # template namespace number


def mw_get_setting(key, default_value=None):
    settings = sublime.load_settings('Mediawiker.sublime-settings')
    return settings.get(key, default_value)


def mw_set_setting(key, value):
    settings = sublime.load_settings('Mediawiker.sublime-settings')
    settings.set(key, value)
    sublime.save_settings('Mediawiker.sublime-settings')


def mw_enco(value):
    ''' for md5 hashing string must be encoded '''
    if pythonver >= 3:
        return value.encode('utf-8')
    return value


def mw_deco(value):
    ''' for py3 decode from bytes '''
    if pythonver >= 3:
        return value.decode('utf-8')
    return value


def mw_dict_val(dictobj, key, default_value=None):
    try:
        return dictobj[key]
    except KeyError:
        if default_value is None:
            return ''
        else:
            return default_value


def mw_get_digest_header(header, username, password, path):
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
    qop = header_attrs['qop'] if 'qop' in header_attrs else 'auth'
    digest_uri = header_attrs['uri'] if 'uri' in header_attrs else path
    algorithm = header_attrs['algorithm'] if 'algorithm' in header_attrs else 'MD5'
    # TODO: ?
    # opaque = header_attrs['opaque'] if 'opaque' in header_attrs else ''
    entity_body = ''  # TODO: ?

    if algorithm == 'MD5':
        ha1 = md5(mw_enco('%s:%s:%s' % (username, realm, password))).hexdigest()
    elif algorithm == 'MD5-Sess':
        ha1 = md5(mw_enco('%s:%s:%s' % (md5(mw_enco('%s:%s:%s' % (username, realm, password))), nonce, cnonce))).hexdigest()

    if 'auth-int' in qop:
        ha2 = md5(mw_enco('%s:%s:%s' % (METHOD, digest_uri, md5(entity_body)))).hexdigest()
    elif 'auth' in qop:
        ha2 = md5(mw_enco('%s:%s' % (METHOD, digest_uri))).hexdigest()

    if 'auth' in qop or 'auth-int' in qop:
        response = md5(mw_enco('%s:%s:%s:%s:%s:%s' % (ha1, nonce, nc, cnonce, qop, ha2))).hexdigest()
    else:
        response = md5(mw_enco('%s:%s:%s' % (ha1, nonce, ha2))).hexdigest()

    # auth = 'username="%s", realm="%s", nonce="%s", uri="%s", response="%s", opaque="%s", qop="%s", nc=%s, cnonce="%s"' % (username, realm, nonce, digest_uri, response, opaque, qop, nc, cnonce)
    auth = 'username="%s", realm="%s", nonce="%s", uri="%s", response="%s", qop="%s", nc=%s, cnonce="%s"' % (username, realm, nonce, digest_uri, response, qop, nc, cnonce)
    return auth


def mw_get_connect(password=''):
    DIGEST_REALM = 'Digest realm'
    BASIC_REALM = 'Basic realm'
    site_name_active = mw_get_setting('mediawiki_site_active')
    site_list = mw_get_setting('mediawiki_site')
    site = site_list[site_name_active]['host']
    path = site_list[site_name_active]['path']
    username = site_list[site_name_active]['username']
    domain = site_list[site_name_active]['domain']
    proxy_host = ''
    if 'proxy_host' in site_list[site_name_active]:
        proxy_host = site_list[site_name_active]['proxy_host']
    is_https = True if 'https' in site_list[site_name_active] and site_list[site_name_active]['https'] else False
    if is_https:
        sublime.status_message('Trying to get https connection to https://%s' % site)
    addr = site if not is_https else ('https', site)
    if proxy_host:
        # proxy_host format is host:port, if only host defined, 80 will be used
        addr = proxy_host if not is_https else ('https', proxy_host)
        proto = 'https' if is_https else 'http'
        path = '%s://%s%s' % (proto, site, path)
        sublime.message_dialog('Connection with proxy: %s %s' % (addr, path))

    try:
        sitecon = mwclient.Site(host=addr, path=path)
    except mwclient.HTTPStatusError as exc:
        e = exc.args if pythonver >= 3 else exc
        is_use_http_auth = mw_dict_val(site_list[site_name_active], 'use_http_auth', False)
        http_auth_login = mw_dict_val(site_list[site_name_active], 'http_auth_login')
        http_auth_password = mw_dict_val(site_list[site_name_active], 'http_auth_password')

        if e[0] == 401 and is_use_http_auth and http_auth_login:
            http_auth_header = e[1].getheader('www-authenticate')
            custom_headers = {}
            realm = None
            if http_auth_header.startswith(BASIC_REALM):
                realm = BASIC_REALM
            elif http_auth_header.startswith(DIGEST_REALM):
                realm = DIGEST_REALM

            if realm is not None:
                if realm == BASIC_REALM:
                    auth = mw_deco(base64.standard_b64encode(mw_enco('%s:%s' % (http_auth_login, http_auth_password))))
                    custom_headers = {'Authorization': 'Basic %s' % auth}
                elif realm == DIGEST_REALM:
                    auth = mw_get_digest_header(http_auth_header, http_auth_login, http_auth_password, '%sapi.php' % path)
                    custom_headers = {'Authorization': 'Digest %s' % auth}

                if custom_headers:
                    sitecon = mwclient.Site(host=addr, path=path, custom_headers=custom_headers)
            else:
                error_message = 'HTTP connection failed: Unknown realm.'
                sublime.status_message(error_message)
                raise Exception(error_message)
        else:
            sublime.status_message('HTTP connection failed: %s' % e[1])
            raise Exception('HTTP connection failed.')

    # if login is not empty - auth required
    if username:
        try:
            sitecon.login(username=username, password=password, domain=domain)
            sublime.status_message('Logon successfully.')
        except mwclient.LoginError as e:
            sublime.status_message('Login failed: %s' % e[1]['result'])
            return
    else:
        sublime.status_message('Connection without authorization')
    return sitecon


def mw_get_page_text(site, title):
    denied_message = 'You have not rights to edit this page. Click OK button to view its source.'
    page = site.Pages[title]
    if page.can('edit'):
        return True, page.edit()
    else:
        if sublime.ok_cancel_dialog(denied_message):
            return False, page.edit()
        else:
            return False, ''


def mw_strunquote(string_value):
    if pythonver >= 3:
        return urllib.parse.unquote(string_value)
    else:
        return urllib.unquote(string_value.encode('ascii')).decode('utf-8')


def mw_strquote(string_value):
    if pythonver >= 3:
        return urllib.parse.quote(string_value)
    else:
        return urllib.quote(string_value.encode('utf-8'))


def mw_pagename_clear(pagename):
    """ Return clear pagename if page-url was set instead of.."""
    site_name_active = mw_get_setting('mediawiki_site_active')
    site_list = mw_get_setting('mediawiki_site')
    site = site_list[site_name_active]['host']
    pagepath = site_list[site_name_active]['pagepath']
    try:
        pagename = mw_strunquote(pagename)
    except UnicodeEncodeError:
        #return pagename
        pass
    except Exception:
        #return pagename
        pass

    if site in pagename:
        pagename = re.sub(r'(https?://)?%s%s' % (site, pagepath), '', pagename)

    sublime.status_message('Page name was cleared.')
    return pagename


def mw_save_mypages(title, storage_name='mediawiker_pagelist'):

    title = title.replace('_', ' ')  # for wiki '_' and ' ' are equal in page name
    pagelist_maxsize = mw_get_setting('mediawiker_pagelist_maxsize')
    site_name_active = mw_get_setting('mediawiki_site_active')
    mediawiker_pagelist = mw_get_setting(storage_name, {})

    if site_name_active not in mediawiker_pagelist:
        mediawiker_pagelist[site_name_active] = []

    my_pages = mediawiker_pagelist[site_name_active]

    if my_pages:
        while len(my_pages) >= pagelist_maxsize:
            my_pages.pop(0)

        if title in my_pages:
            #for sorting
            my_pages.remove(title)
    my_pages.append(title)
    mw_set_setting(storage_name, mediawiker_pagelist)


def mw_get_title():
    ''' returns page title of active tab from view_name or from file_name'''

    view_name = sublime.active_window().active_view().name()
    if view_name:
        return view_name
    else:
        #haven't view.name, try to get from view.file_name (without extension)
        file_name = sublime.active_window().active_view().file_name()
        if file_name:
            wiki_extensions = mw_get_setting('mediawiker_files_extension')
            title, ext = splitext(basename(file_name))
            if ext[1:] in wiki_extensions and title:
                return title
            else:
                sublime.status_message('Anauthorized file extension for mediawiki publishing. Check your configuration for correct extensions.')
                return ''
    return ''


def mw_get_hlevel(header_string, substring):
    return int(header_string.count(substring) / 2)


def mw_get_category(category_full_name):
    ''' From full category name like "Category:Name" return tuple (Category, Name) '''
    if ':' in category_full_name:
        return category_full_name.split(':')
    else:
        return 'Category', category_full_name


def mw_get_page_url(page_name=''):
    site_name_active = mw_get_setting('mediawiki_site_active')
    site_list = mw_get_setting('mediawiki_site')
    site = site_list[site_name_active]["host"]

    is_https = False
    if 'https' in site_list[site_name_active]:
        is_https = site_list[site_name_active]["https"]

    proto = 'https' if is_https else 'http'
    pagepath = site_list[site_name_active]["pagepath"]
    if not page_name:
        page_name = mw_strquote(mw_get_title())
    if page_name:
        return '%s://%s%s%s' % (proto, site, pagepath, page_name)
    else:
        return ''


class MediawikerInsertTextCommand(sublime_plugin.TextCommand):

    def run(self, edit, position, text):
        self.view.insert(edit, position, text)


class MediawikerPageCommand(sublime_plugin.WindowCommand):
    '''prepare all actions with wiki'''

    action = ''
    is_inputfixed = False
    run_in_new_window = False

    def run(self, action, title=''):
        self.action = action
        actions_validate = ['mediawiker_publish_page', 'mediawiker_add_category',
                            'mediawiker_category_list', 'mediawiker_search_string_list',
                            'mediawiker_add_image', 'mediawiker_add_template',
                            'mediawiker_upload']

        if self.action == 'mediawiker_show_page':
            if mw_get_setting('mediawiker_newtab_ongetpage'):
                self.run_in_new_window = True

            if not title:
                pagename_default = ''
                # use clipboard or selected text for page name
                if bool(mw_get_setting('mediawiker_clipboard_as_defaultpagename')):
                    pagename_default = sublime.get_clipboard().strip()
                if not pagename_default:
                    selection = self.window.active_view().sel()
                    # for selreg in selection:
                    #     pagename_default = self.window.active_view().substr(selreg).strip()
                    #     break
                    pagename_default = self.window.active_view().substr(selection[0]).strip()
                self.window.show_input_panel('Wiki page name:', mw_pagename_clear(pagename_default), self.on_done, self.on_change, None)
            else:
                self.on_done(title)
        elif self.action == 'mediawiker_reopen_page':
            #get page name
            if not title:
                title = mw_get_title()
            self.action = 'mediawiker_show_page'
            self.on_done(title)
        elif self.action in actions_validate:
            self.on_done('')

    def on_change(self, title):
        if title:
            pagename_cleared = mw_pagename_clear(title)
            if title != pagename_cleared:
                self.window.show_input_panel('Wiki page name:', pagename_cleared, self.on_done, self.on_change, None)

    def on_done(self, title):
        if self.run_in_new_window:
            sublime.active_window().new_file()
            self.run_in_new_window = False
        try:
            if title:
                title = mw_pagename_clear(title)
            self.window.run_command("mediawiker_validate_connection_params", {"title": title, "action": self.action})
        except ValueError as e:
            sublime.message_dialog(e)


class MediawikerOpenPageCommand(sublime_plugin.WindowCommand):
    ''' alias to Get page command '''

    def run(self):
        self.window.run_command("mediawiker_page", {"action": "mediawiker_show_page"})


class MediawikerReopenPageCommand(sublime_plugin.WindowCommand):

    def run(self):
        self.window.run_command("mediawiker_page", {"action": "mediawiker_reopen_page"})


class MediawikerPostPageCommand(sublime_plugin.WindowCommand):
    ''' alias to Publish page command '''

    def run(self):
        self.window.run_command("mediawiker_page", {"action": "mediawiker_publish_page"})


class MediawikerSetCategoryCommand(sublime_plugin.WindowCommand):
    ''' alias to Add category command '''

    def run(self):
        self.window.run_command("mediawiker_page", {"action": "mediawiker_add_category"})


class MediawikerInsertImageCommand(sublime_plugin.WindowCommand):
    ''' alias to Add image command '''

    def run(self):
        self.window.run_command("mediawiker_page", {"action": "mediawiker_add_image"})


class MediawikerInsertTemplateCommand(sublime_plugin.WindowCommand):
    ''' alias to Add template command '''

    def run(self):
        self.window.run_command("mediawiker_page", {"action": "mediawiker_add_template"})


class MediawikerFileUploadCommand(sublime_plugin.WindowCommand):
    ''' alias to Add template command '''

    def run(self):
        self.window.run_command("mediawiker_page", {"action": "mediawiker_upload"})


class MediawikerCategoryTreeCommand(sublime_plugin.WindowCommand):
    ''' alias to Category list command '''

    def run(self):
        self.window.run_command("mediawiker_page", {"action": "mediawiker_category_list"})


class MediawikerSearchStringCommand(sublime_plugin.WindowCommand):
    ''' alias to Search string list command '''

    def run(self):
        self.window.run_command("mediawiker_page", {"action": "mediawiker_search_string_list"})


class MediawikerPageListCommand(sublime_plugin.WindowCommand):

    def run(self, storage_name='mediawiker_pagelist'):
        site_name_active = mw_get_setting('mediawiki_site_active')
        mediawiker_pagelist = mw_get_setting(storage_name, {})
        self.my_pages = mediawiker_pagelist[site_name_active] if site_name_active in mediawiker_pagelist else []
        if self.my_pages:
            self.my_pages.reverse()
            #error 'Quick panel unavailable' fix with timeout..
            sublime.set_timeout(lambda: self.window.show_quick_panel(self.my_pages, self.on_done), 1)
        else:
            sublime.status_message('List of pages for wiki "%s" is empty.' % (site_name_active))

    def on_done(self, index):
        if index >= 0:
            # escape from quick panel return -1
            title = self.my_pages[index]
            try:
                self.window.run_command("mediawiker_page", {"title": title, "action": "mediawiker_show_page"})
            except ValueError as e:
                sublime.message_dialog(e)


class MediawikerValidateConnectionParamsCommand(sublime_plugin.WindowCommand):
    site = None
    password = ''
    title = ''
    action = ''
    is_hide_password = False
    PASSWORD_CHAR = u'\u25CF'

    def run(self, title, action):
        self.is_hide_password = mw_get_setting('mediawiker_password_input_hide')
        self.PASSWORD_CHAR = mw_get_setting('mediawiker_password_char')
        self.action = action  # TODO: check for better variant
        self.title = title
        site = mw_get_setting('mediawiki_site_active')
        site_list = mw_get_setting('mediawiki_site')
        self.password = site_list[site]["password"]
        if site_list[site]["username"]:
            # auth required if username exists in settings
            if not self.password:
                # need to ask for password
                self.window.show_input_panel('Password:', '', self.on_done, self.on_change, None)
            else:
                self.call_page()
        else:
            # auth is not required
            self.call_page()

    def _get_password(self, str_val):
        self.password = self.password + str_val.replace(self.PASSWORD_CHAR, '')
        return self.PASSWORD_CHAR * len(self.password)

    def on_change(self, str_val):
        if str_val:
            if self.is_hide_password:
                # password hiding hack..
                if str_val:
                    password = str_val
                    str_val = self._get_password(str_val)
                    if password != str_val:
                        password = str_val
                        self.window.show_input_panel('Password:', str_val, self.on_done, self.on_change, None)
        else:
            self.password = ''

    def on_done(self, password):
        if not self.is_hide_password:
            self.password = password
        self.call_page()

    def call_page(self):
        self.window.active_view().run_command(self.action, {"title": self.title, "password": self.password})


class MediawikerShowPageCommand(sublime_plugin.TextCommand):

    def run(self, edit, title, password):
        is_writable = False
        sitecon = mw_get_connect(password)
        is_writable, text = mw_get_page_text(sitecon, title)
        if is_writable and not text:
            sublime.status_message('Wiki page %s is not exists. You can create new..' % (title))
            text = '<New wiki page: Remove this with text of the new page>'
        if is_writable:
            self.view.erase(edit, sublime.Region(0, self.view.size()))
            self.view.set_syntax_file('Packages/Mediawiker/Mediawiki.tmLanguage')
            self.view.set_name(title)
            self.view.run_command('mediawiker_insert_text', {'position': 0, 'text': text})
            sublime.status_message('Page %s was opened successfully.' % (title))


class MediawikerPublishPageCommand(sublime_plugin.TextCommand):
    my_pages = None
    page = None
    title = ''
    current_text = ''

    def run(self, edit, title, password):
        sitecon = mw_get_connect(password)
        self.title = mw_get_title()
        if self.title:
            self.page = sitecon.Pages[self.title]
            if self.page.can('edit'):
                self.current_text = self.view.substr(sublime.Region(0, self.view.size()))
                summary_message = 'Changes summary (%s):' % mw_get_setting('mediawiki_site_active')
                self.view.window().show_input_panel(summary_message, '', self.on_done, None, None)
            else:
                sublime.status_message('You have not rights to edit this page')
        else:
            sublime.status_message('Can\'t publish page with empty title')
            return

    def on_done(self, summary):
        try:
            summary = '%s%s' % (summary, mw_get_setting('mediawiker_summary_postfix', ' (by SublimeText.Mediawiker)'))
            mark_as_minor = mw_get_setting('mediawiker_mark_as_minor')
            if self.page.can('edit'):
                #invert minor settings command '!'
                if summary[0] == '!':
                    mark_as_minor = not mark_as_minor
                    summary = summary[1:]
                self.page.save(self.current_text, summary=summary.strip(), minor=mark_as_minor)
            else:
                sublime.status_message('You have not rights to edit this page')
        except mwclient.EditError as e:
            sublime.status_message('Can\'t publish page %s (%s)' % (self.title, e))
        sublime.status_message('Wiki page %s was successfully published to wiki.' % (self.title))
        #save my pages
        mw_save_mypages(self.title)


class MediawikerShowTocCommand(sublime_plugin.TextCommand):
    items = []
    regions = []
    pattern = r'^(={1,5})\s?(.*?)\s?={1,5}'

    def run(self, edit):
        self.items = []
        self.regions = []
        self.regions = self.view.find_all(self.pattern)
        #self.items = map(self.get_header, self.regions)
        self.items = [self.get_header(x) for x in self.regions]
        sublime.set_timeout(lambda: self.view.window().show_quick_panel(self.items, self.on_done), 1)

    def get_header(self, region):
        TAB_SIZE = ' ' * 4
        return re.sub(self.pattern, r'\1\2', self.view.substr(region)).replace('=', TAB_SIZE)[len(TAB_SIZE):]

    def on_done(self, index):
        if index >= 0:
            # escape from quick panel returns -1
            self.view.show(self.regions[index])
            self.view.sel().clear()
            self.view.sel().add(self.regions[index])


class MediawikerShowInternalLinksCommand(sublime_plugin.TextCommand):
    items = []
    regions = []
    pattern = r'\[{2}(.*?)(\|.*?)?\]{2}'
    actions = ['Goto internal link', 'Open page in editor', 'Open page in browser']
    selected = None

    def run(self, edit):
        self.items = []
        self.regions = []
        self.regions = self.view.find_all(self.pattern)
        self.items = [mw_strunquote(self.get_header(x)) for x in self.regions]
        if self.items:
            sublime.set_timeout(lambda: self.view.window().show_quick_panel(self.items, self.on_select), 1)
        else:
            sublime.status_message('No internal links was found.')

    def get_header(self, region):
        return re.sub(self.pattern, r'\1', self.view.substr(region))

    def on_select(self, index):
        if index >= 0:
            self.selected = index
            sublime.set_timeout(lambda: self.view.window().show_quick_panel(self.actions, self.on_done), 1)

    def on_done(self, index):
        if index == 0:
            # escape from quick panel returns -1
            self.view.show(self.regions[self.selected])
            self.view.sel().clear()
            self.view.sel().add(self.regions[self.selected])
        elif index == 1:
            sublime.set_timeout(lambda: self.view.window().run_command("mediawiker_page", {"action": "mediawiker_show_page", "title": self.items[self.selected]}), 1)
        elif index == 2:
            url = mw_get_page_url(self.items[self.selected])
            webbrowser.open(url)


class MediawikerShowExternalLinksCommand(sublime_plugin.TextCommand):
    items = []
    regions = []
    pattern = r'[^\[]\[{1}(\w.*?)(\s.*?)?\]{1}[^\]]'
    actions = ['Goto external link', 'Open link in browser']
    selected = None

    def run(self, edit):
        self.items = []
        self.regions = []
        self.regions = self.view.find_all(self.pattern)
        self.items = [self.get_header(x) for x in self.regions]
        self.urls = [self.get_url(x) for x in self.regions]
        if self.items:
            sublime.set_timeout(lambda: self.view.window().show_quick_panel(self.items, self.on_select), 1)
        else:
            sublime.status_message('No external links was found.')

    def prepare_header(self, header):
        maxlen = 70
        link_url = mw_strunquote(header.group(1))
        link_descr = re.sub(r'<.*?>', '', header.group(2))
        postfix = '..' if len(link_descr) > maxlen else ''
        return '%s: %s%s' % (link_url, link_descr[:maxlen], postfix)

    def get_header(self, region):
        # return re.sub(self.pattern, r'\1: \2', self.view.substr(region))
        return re.sub(self.pattern, self.prepare_header, self.view.substr(region))

    def get_url(self, region):
        return re.sub(self.pattern, r'\1', self.view.substr(region))

    def on_select(self, index):
        if index >= 0:
            self.selected = index
            sublime.set_timeout(lambda: self.view.window().show_quick_panel(self.actions, self.on_done), 1)

    def on_done(self, index):
        if index == 0:
            # escape from quick panel returns -1
            self.view.show(self.regions[self.selected])
            self.view.sel().clear()
            self.view.sel().add(self.regions[self.selected])
        elif index == 1:
            webbrowser.open(self.urls[self.selected])


class MediawikerEnumerateTocCommand(sublime_plugin.TextCommand):
    items = []
    regions = []

    def run(self, edit):
        self.items = []
        self.regions = []
        pattern = '^={1,5}(.*)?={1,5}'
        self.regions = self.view.find_all(pattern)
        header_level_number = [0, 0, 0, 0, 0]
        len_delta = 0
        for r in self.regions:
            if len_delta:
                #prev. header text was changed, move region to new position
                r_new = sublime.Region(r.a + len_delta, r.b + len_delta)
            else:
                r_new = r
            region_len = r_new.b - r_new.a
            header_text = self.view.substr(r_new)
            level = mw_get_hlevel(header_text, "=")
            current_number_str = ''
            i = 1
            #generate number value, start from 1
            while i <= level:
                position_index = i - 1
                header_number = header_level_number[position_index]
                if i == level:
                    #incr. number
                    header_number += 1
                    #save current number
                    header_level_number[position_index] = header_number
                    #reset sub-levels numbers
                    header_level_number[i:] = [0] * len(header_level_number[i:])
                if header_number:
                    current_number_str = "%s.%s" % (current_number_str, header_number) if current_number_str else '%s' % (header_number)
                #incr. level
                i += 1

            #get title only
            header_text_clear = header_text.strip(' =\t')
            header_text_clear = re.sub(r'^(\d\.)+\s+(.*)', r'\2', header_text_clear)
            header_tag = '=' * level
            header_text_numbered = '%s %s. %s %s' % (header_tag, current_number_str, header_text_clear, header_tag)
            len_delta += len(header_text_numbered) - region_len
            self.view.replace(edit, r_new, header_text_numbered)


class MediawikerSetActiveSiteCommand(sublime_plugin.WindowCommand):
    site_keys = []
    site_on = '>'
    site_off = ' ' * 3
    site_active = ''

    def run(self):
        self.site_active = mw_get_setting('mediawiki_site_active')
        sites = mw_get_setting('mediawiki_site')
        #self.site_keys = map(self.is_checked, list(sites.keys()))
        self.site_keys = [self.is_checked(x) for x in sites.keys()]
        sublime.set_timeout(lambda: self.window.show_quick_panel(self.site_keys, self.on_done), 1)

    def is_checked(self, site_key):
        checked = self.site_on if site_key == self.site_active else self.site_off
        return '%s %s' % (checked, site_key)

    def on_done(self, index):
        # not escaped and not active
        if index >= 0 and not self.site_keys[index].startswith(self.site_on):
            mw_set_setting("mediawiki_site_active", self.site_keys[index].strip())


class MediawikerOpenPageInBrowserCommand(sublime_plugin.WindowCommand):
    def run(self):
        url = mw_get_page_url()
        if url:
            webbrowser.open(url)
        else:
            sublime.status_message('Can\'t open page with empty title')
            return


class MediawikerAddCategoryCommand(sublime_plugin.TextCommand):
    categories_list = None
    title = ''
    sitecon = None

    category_root = ''
    category_options = [['Set category', ''], ['Open category', ''], ['Back to root', '']]

    # TODO: back in category tree..

    def run(self, edit, title, password):
        self.sitecon = mw_get_connect(password)
        self.category_root = mw_get_category(mw_get_setting('mediawiker_category_root'))[1]
        sublime.active_window().show_input_panel('Wiki root category:', self.category_root, self.get_category_menu, None, None)
        #self.get_category_menu(self.category_root)

    def get_category_menu(self, category_root):
        category = self.sitecon.Categories[category_root]
        self.categories_list_names = []
        self.categories_list_values = []

        for page in category:
            if page.namespace == CATEGORY_NAMESPACE:
                self.categories_list_values.append(page.name)
                self.categories_list_names.append(page.name[page.name.find(':') + 1:])
        sublime.set_timeout(lambda: sublime.active_window().show_quick_panel(self.categories_list_names, self.on_done), 1)

    def on_done(self, idx):
        # the dialog was cancelled
        if idx >= 0:
            self.category_options[0][1] = self.categories_list_values[idx]
            self.category_options[1][1] = self.categories_list_names[idx]
            sublime.set_timeout(lambda: sublime.active_window().show_quick_panel(self.category_options, self.on_done_final), 1)

    def on_done_final(self, idx):
        if idx == 0:
            # set category
            index_of_textend = self.view.size()
            self.view.run_command('mediawiker_insert_text', {'position': index_of_textend, 'text': '[[%s]]' % self.category_options[idx][1]})
        elif idx == 1:
            self.get_category_menu(self.category_options[idx][1])
        else:
            self.get_category_menu(self.category_root)


class MediawikerCsvTableCommand(sublime_plugin.TextCommand):
    ''' selected text, csv data to wiki table '''

    delimiter = '|'

    # TODO: rewrite as simple to wiki command
    def run(self, edit):
        self.delimiter = mw_get_setting('mediawiker_csvtable_delimiter', '|')
        table_header = '{|'
        table_footer = '|}'
        table_properties = ' '.join(['%s="%s"' % (prop, value) for prop, value in mw_get_setting('mediawiker_wikitable_properties', {}).items()])
        cell_properties = ' '.join(['%s="%s"' % (prop, value) for prop, value in mw_get_setting('mediawiker_wikitable_cell_properties', {}).items()])
        if cell_properties:
            cell_properties = ' %s | ' % cell_properties

        for region in self.view.sel():
            table_data_dic_tmp = []
            table_data = ''
            #table_data_dic_tmp = map(self.get_table_data, self.view.substr(region).split('\n'))
            table_data_dic_tmp = [self.get_table_data(x) for x in self.view.substr(region).split('\n')]

            # verify and fix columns count in rows
            if table_data_dic_tmp:
                cols_cnt = len(max(table_data_dic_tmp, key=len))
                for row in table_data_dic_tmp:
                    if row:
                        while cols_cnt - len(row):
                            row.append('')

                for row in table_data_dic_tmp:
                    if row:
                        if table_data:
                            table_data += '\n|-\n'
                            column_separator = '||'
                        else:
                            table_data += '|-\n'
                            column_separator = '!!'

                        for col in row:
                            col_sep = column_separator if row.index(col) else column_separator[0]
                            table_data += '%s%s%s ' % (col_sep, cell_properties, col)

                self.view.replace(edit, region, '%s %s\n%s\n%s' % (table_header, table_properties, table_data, table_footer))

    def get_table_data(self, line):
        if self.delimiter in line:
            return line.split(self.delimiter)
        return []


class MediawikerEditPanelCommand(sublime_plugin.WindowCommand):
    options = []
    SNIPPET_CHAR = u'\u24C8'

    def run(self):
        self.SNIPPET_CHAR = mw_get_setting('mediawiker_snippet_char')
        self.options = mw_get_setting('mediawiker_panel', {})
        if self.options:
            office_panel_list = ['\t%s' % val['caption'] if val['type'] != 'snippet' else '\t%s %s' % (self.SNIPPET_CHAR, val['caption']) for val in self.options]
            self.window.show_quick_panel(office_panel_list, self.on_done)

    def on_done(self, index):
        if index >= 0:
            # escape from quick panel return -1
            try:
                action_type = self.options[index]['type']
                action_value = self.options[index]['value']
                if action_type == 'snippet':
                    # run snippet
                    self.window.active_view().run_command("insert_snippet", {"name": action_value})
                elif action_type == 'window_command':
                    # run command
                    self.window.run_command(action_value)
                elif action_type == 'text_command':
                    # run command
                    self.window.active_view().run_command(action_value)
            except ValueError as e:
                sublime.status_message(e)


class MediawikerTableWikiToSimpleCommand(sublime_plugin.TextCommand):
    ''' convert selected (or under cursor) wiki table to Simple table (TableEdit plugin) '''

    # TODO: wiki table properties will be lost now...
    def run(self, edit):
        selection = self.view.sel()
        table_region = None

        if not self.view.substr(selection[0]):
            table_region = self.table_getregion()
        else:
            table_region = selection[0]  # only first region will be proceed..

        if table_region:
            text = self.view.substr(table_region)
            text = self.table_fixer(text)
            self.view.replace(edit, table_region, self.table_get(text))
            # Turn on TableEditor
            try:
                self.view.run_command('table_editor_enable_for_current_view', {'prop': 'enable_table_editor'})
            except Exception as e:
                sublime.status_message('Need to correct install plugin TableEditor: %s' % e)

    def table_get(self, text):
        tbl_row_delimiter = r'\|\-(.*)'
        tbl_cell_delimiter = r'\n\s?\||\|\||\n\s?\!|\!\!'  # \n| or || or \n! or !!
        rows = re.split(tbl_row_delimiter, text)

        tbl_full = []
        for row in rows:
            if row and row[0] != '{':
                tbl_row = []
                cells = re.split(tbl_cell_delimiter, row, re.DOTALL)[1:]
                for cell in cells:
                    cell = cell.replace('\n', '')
                    cell = ' ' if not cell else cell
                    if cell[0] != '{' and cell[-1] != '}':
                        cell = self.delim_fixer(cell)
                        tbl_row.append(cell)
                tbl_full.append(tbl_row)

        tbl_full = self.table_print(tbl_full)
        return tbl_full

    def table_print(self, table_data):
        CELL_LEFT_BORDER = '|'
        CELL_RIGHT_BORDER = ''
        ROW_LEFT_BORDER = ''
        ROW_RIGHT_BORDER = '|'
        tbl_print = ''
        for row in table_data:
            if row:
                row_print = ''.join(['%s%s%s' % (CELL_LEFT_BORDER, cell, CELL_RIGHT_BORDER) for cell in row])
                row_print = '%s%s%s' % (ROW_LEFT_BORDER, row_print, ROW_RIGHT_BORDER)
                tbl_print += '%s\n' % (row_print)
        return tbl_print

    def table_getregion(self):
        cursor_position = self.view.sel()[0].begin()
        pattern = r'^\{\|(.*?\n?)*\|\}'
        regions = self.view.find_all(pattern)
        for reg in regions:
            if reg.a <= cursor_position <= reg.b:
                return reg

    def table_fixer(self, text):
        text = re.sub(r'(\{\|.*\n)(\s?)(\||\!)(\s?[^-])', r'\1\2|-\n\3\4', text)  # if |- skipped after {| line, add it
        return text

    def delim_fixer(self, string_data):
        REPLACE_STR = ':::'
        return string_data.replace('|', REPLACE_STR)


class MediawikerTableSimpleToWikiCommand(sublime_plugin.TextCommand):
    ''' convert selected (or under cursor) Simple table (TableEditor plugin) to wiki table '''
    def run(self, edit):
        selection = self.view.sel()
        table_region = None
        if not self.view.substr(selection[0]):
            table_region = self.gettable()
        else:
            table_region = selection[0]  # only first region will be proceed..

        if table_region:
            text = self.view.substr(table_region)
            table_data = self.table_parser(text)
            self.view.replace(edit, table_region, self.drawtable(table_data))

    def table_parser(self, text):
        table_data = []
        TBL_HEADER_STRING = '|-'
        need_header = False
        if text.split('\n')[1][:2] == TBL_HEADER_STRING:
            need_header = True
        for line in text.split('\n'):
            if line:
                row_data = []
                if line[:2] == TBL_HEADER_STRING:
                    continue
                elif line[0] == '|':
                    cells = line[1:-1].split('|')  # without first and last char "|"
                    for cell_data in cells:
                        row_data.append({'properties': '', 'cell_data': cell_data, 'is_header': need_header})
                    if need_header:
                        need_header = False
            if row_data and type(row_data) is list:
                table_data.append(row_data)
        return table_data

    def gettable(self):
        cursor_position = self.view.sel()[0].begin()
        # ^([^\|\n].*)?\n\|(.*\n)*?\|.*\n[^\|] - all tables regexp (simple and wiki)?
        pattern = r'^\|(.*\n)*?\|.*\n[^\|]'
        regions = self.view.find_all(pattern)
        for reg in regions:
            if reg.a <= cursor_position <= reg.b:
                table_region = sublime.Region(reg.a, reg.b - 2)  # minus \n and [^\|]
                return table_region

    def drawtable(self, table_list):
        ''' draw wiki table '''
        TBL_START = '{|'
        TBL_STOP = '|}'
        TBL_ROW_START = '|-'
        CELL_FIRST_DELIM = '|'
        CELL_DELIM = '||'
        CELL_HEAD_FIRST_DELIM = '!'
        CELL_HEAD_DELIM = '!!'
        REPLACE_STR = ':::'

        text_wikitable = ''
        table_properties = ' '.join(['%s="%s"' % (prop, value) for prop, value in mw_get_setting('mediawiker_wikitable_properties', {}).items()])

        need_header = table_list[0][0]['is_header']
        is_first_line = True
        for row in table_list:
            if need_header or is_first_line:
                text_wikitable += '%s\n%s' % (TBL_ROW_START, CELL_HEAD_FIRST_DELIM)
                text_wikitable += self.getrow(CELL_HEAD_DELIM, row)
                is_first_line = False
                need_header = False
            else:
                text_wikitable += '\n%s\n%s' % (TBL_ROW_START, CELL_FIRST_DELIM)
                text_wikitable += self.getrow(CELL_DELIM, row)
                text_wikitable = text_wikitable.replace(REPLACE_STR, '|')

        return '%s %s\n%s\n%s' % (TBL_START, table_properties, text_wikitable, TBL_STOP)

    def getrow(self, delimiter, rowlist=[]):
        cell_properties = ' '.join(['%s="%s"' % (prop, value) for prop, value in mw_get_setting('mediawiker_wikitable_cell_properties', {}).items()])
        cell_properties = '%s | ' % cell_properties if cell_properties else ''
        try:
            return delimiter.join(' %s%s ' % (cell_properties, cell['cell_data'].strip()) for cell in rowlist)
        except Exception as e:
            print('Error in data: %s' % e)


class MediawikerCategoryListCommand(sublime_plugin.TextCommand):
    password = ''
    pages = {}  # pagenames -> namespaces
    pages_names = []  # pagenames for menu
    category_path = []
    CATEGORY_NEXT_PREFIX_MENU = '> '
    CATEGORY_PREV_PREFIX_MENU = '. . '
    category_prefix = ''  # "Category" namespace name as returned language..

    def run(self, edit, title, password):
        self.password = password
        if self.category_path:
            category_root = mw_get_category(self.get_category_current())[1]
        else:
            category_root = mw_get_category(mw_get_setting('mediawiker_category_root'))[1]
        sublime.active_window().show_input_panel('Wiki root category:', category_root, self.show_list, None, None)

    def show_list(self, category_root):
        if not category_root:
            return
        self.pages = {}
        self.pages_names = []

        category_root = mw_get_category(category_root)[1]

        if not self.category_path:
            self.update_category_path('%s:%s' % (self.get_category_prefix(), category_root))

        if len(self.category_path) > 1:
            self.add_page(self.get_category_prev(), CATEGORY_NAMESPACE, False)

        for page in self.get_list_data(category_root):
            if page.namespace == CATEGORY_NAMESPACE and not self.category_prefix:
                    self.category_prefix = mw_get_category(page.name)[0]
            self.add_page(page.name, page.namespace, True)
        if self.pages:
            self.pages_names.sort()
            sublime.set_timeout(lambda: sublime.active_window().show_quick_panel(self.pages_names, self.get_page), 1)
        else:
            sublime.message_dialog('Category %s is empty' % category_root)

    def add_page(self, page_name, page_namespace, as_next=True):
        page_name_menu = page_name
        if page_namespace == CATEGORY_NAMESPACE:
            page_name_menu = self.get_category_as_next(page_name) if as_next else self.get_category_as_prev(page_name)
        self.pages[page_name] = page_namespace
        self.pages_names.append(page_name_menu)

    def get_list_data(self, category_root):
        ''' get objects list by category name '''
        sitecon = mw_get_connect(self.password)
        return sitecon.Categories[category_root]

    def get_category_as_next(self, category_string):
        return '%s%s' % (self.CATEGORY_NEXT_PREFIX_MENU, category_string)

    def get_category_as_prev(self, category_string):
        return '%s%s' % (self.CATEGORY_PREV_PREFIX_MENU, category_string)

    def category_strip_special_prefix(self, category_string):
        return category_string.lstrip(self.CATEGORY_NEXT_PREFIX_MENU).lstrip(self.CATEGORY_PREV_PREFIX_MENU)

    def get_category_prev(self):
        ''' return previous category name in format Category:CategoryName'''
        return self.category_path[-2]

    def get_category_current(self):
        ''' return current category name in format Category:CategoryName'''
        return self.category_path[-1]

    def get_category_prefix(self):
        if self.category_prefix:
            return self.category_prefix
        else:
            return 'Category'

    def update_category_path(self, category_string):
        if category_string in self.category_path:
            self.category_path = self.category_path[:-1]
        else:
            self.category_path.append(self.category_strip_special_prefix(category_string))

    def get_page(self, index):
        if index >= 0:
            # escape from quick panel return -1
            page_name = self.category_strip_special_prefix(self.pages_names[index])
            if self.pages[page_name] == CATEGORY_NAMESPACE:
                self.update_category_path(page_name)
                self.show_list(page_name)
            else:
                try:
                    sublime.active_window().run_command("mediawiker_page", {"title": page_name, "action": "mediawiker_show_page"})
                except ValueError as e:
                    sublime.message_dialog(e)


class MediawikerSearchStringListCommand(sublime_plugin.TextCommand):
    password = ''
    title = ''
    search_limit = 20
    pages_names = []
    search_result = None

    def run(self, edit, title, password):
        self.password = password
        sublime.active_window().show_input_panel('Wiki search:', '', self.show_results, None, None)

    def show_results(self, search_value=''):
        #TODO: paging?
        self.pages_names = []
        self.search_limit = mw_get_setting('mediawiker_search_results_count')
        if search_value:
            self.search_result = self.do_search(search_value)
        if self.search_result:
            for i in range(self.search_limit):
                try:
                    page_data = self.search_result.next()
                    self.pages_names.append([page_data['title'], page_data['snippet']])
                except:
                    pass
            te = ''
            search_number = 1
            for pa in self.pages_names:
                te += '### %s. %s\n* [%s](%s)\n\n%s\n' % (search_number, pa[0], pa[0], mw_get_page_url(pa[0]), self.antispan(pa[1]))
                search_number += 1

            if te:
                self.view = sublime.active_window().new_file()
                self.view.set_syntax_file('Packages/Markdown/Markdown.tmLanguage')
                self.view.set_name('Wiki search results: %s' % search_value)
                self.view.run_command('mediawiker_insert_text', {'position': 0, 'text': te})
            elif search_value:
                sublime.message_dialog('No results for: %s' % search_value)

    def antispan(self, text):
        span_replace_open = "`"
        span_replace_close = "`"
        #bold and italic tags cut
        text = text.replace("'''", "")
        text = text.replace("''", "")
        #spans to bold
        text = re.sub(r'<span(.*?)>', span_replace_open, text)
        text = re.sub(r'<\/span>', span_replace_close, text)
        #divs cut
        text = re.sub(r'<div(.*?)>', '', text)
        text = re.sub(r'<\/div>', '', text)
        return text

    def do_search(self, string_value):
        sitecon = mw_get_connect(self.password)
        namespace = mw_get_setting('mediawiker_search_namespaces')
        return sitecon.search(search=string_value, what='text', limit=self.search_limit, namespace=namespace)


class MediawikerAddImageCommand(sublime_plugin.TextCommand):
    password = ''
    image_prefix_min_lenght = 4
    images_names = []

    def run(self, edit, password, title=''):
        self.password = password
        self.image_prefix_min_lenght = mw_get_setting('mediawiker_image_prefix_min_length', 4)
        sublime.active_window().show_input_panel('Wiki image prefix (min %s):' % self.image_prefix_min_lenght, '', self.show_list, None, None)

    def show_list(self, image_prefix):
        if len(image_prefix) >= self.image_prefix_min_lenght:
            sitecon = mw_get_connect(self.password)
            images = sitecon.allpages(prefix=image_prefix, namespace=IMAGE_NAMESPACE)  # images list by prefix
            #self.images_names = map(self.get_page_title, images)
            self.images_names = [self.get_page_title(x) for x in images]
            sublime.set_timeout(lambda: sublime.active_window().show_quick_panel(self.images_names, self.on_done), 1)
        else:
            sublime.message_dialog('Image prefix length must be more than %s. Operation canceled.' % self.image_prefix_min_lenght)

    def get_page_title(self, obj):
        return obj.page_title

    def on_done(self, idx):
        if idx >= 0:
            index_of_cursor = self.view.sel()[0].begin()
            self.view.run_command('mediawiker_insert_text', {'position': index_of_cursor, 'text': '[[Image:%s]]' % self.images_names[idx]})


class MediawikerAddTemplateCommand(sublime_plugin.TextCommand):
    password = ''
    templates_names = []
    sitecon = None

    def run(self, edit, password, title=''):
        self.password = password
        sublime.active_window().show_input_panel('Wiki template prefix:', '', self.show_list, None, None)

    def show_list(self, image_prefix):
        self.templates_names = []
        self.sitecon = mw_get_connect(self.password)
        templates = self.sitecon.allpages(prefix=image_prefix, namespace=TEMPLATE_NAMESPACE)  # images list by prefix
        for template in templates:
            self.templates_names.append(template.page_title)
        sublime.set_timeout(lambda: sublime.active_window().show_quick_panel(self.templates_names, self.on_done), 1)

    def get_template_params(self, text):
        params_list = []
        pattern = r'\{{3}.*?\}{3}'
        parameters = re.findall(pattern, text)
        for param in parameters:
            param = param.strip('{}')
            #default value or not..
            param = param.replace('|', '=') if '|' in param else '%s=' % param
            if param not in params_list:
                params_list.append(param)
        return ''.join(['|%s\n' % param for param in params_list])

    def on_done(self, idx):
        if idx >= 0:
            template = self.sitecon.Pages['Template:%s' % self.templates_names[idx]]
            text = template.edit()
            params_text = self.get_template_params(text)
            index_of_cursor = self.view.sel()[0].begin()
            template_text = '{{%s%s}}' % (self.templates_names[idx], params_text)
            self.view.run_command('mediawiker_insert_text', {'position': index_of_cursor, 'text': template_text})


class MediawikerCliCommand(sublime_plugin.WindowCommand):

    def run(self, url):
        if url:
            # print('Opening page: %s' % url)
            sublime.set_timeout(lambda: self.window.run_command("mediawiker_page", {"action": "mediawiker_show_page", "title": self.proto_replacer(url)}), 1)

    def proto_replacer(self, url):
        if sublime.platform() == 'windows' and url.endswith('/'):
            url = url[:-1]
        elif sublime.platform() == 'linux' and url.startswith("'") and url.endswith("'"):
            url = url[1:-1]
        return url.split("://")[1]


class MediawikerUploadCommand(sublime_plugin.TextCommand):

    password = None
    file_path = None
    file_destname = None
    file_descr = None

    def run(self, edit, password, title=''):
        self.password = password
        sublime.active_window().show_input_panel('File path:', '', self.get_destfilename, None, None)

    def get_destfilename(self, file_path):
        if file_path:
            self.file_path = file_path
            file_destname = basename(file_path)
            sublime.active_window().show_input_panel('Destination file name [%s]:' % (file_destname), file_destname, self.get_filedescr, None, None)

    def get_filedescr(self, file_destname):
        if not file_destname:
            file_destname = basename(self.file_path)
        self.file_destname = file_destname
        sublime.active_window().show_input_panel('File description:', '', self.on_done, None, None)

    def on_done(self, file_descr=''):
        sitecon = mw_get_connect(self.password)
        if file_descr:
            self.file_descr = file_descr
        else:
            self.file_descr = '%s as %s' % (basename(self.file_path), self.file_destname)
        try:
            with open(self.file_path, 'rb') as f:
                sitecon.upload(f, self.file_destname, self.file_descr)
            sublime.status_message('File %s successfully uploaded to wiki as %s' % (self.file_path, self.file_destname))
        except IOError as e:
            sublime.message_dialog('Upload io error: %s' % e)
        except Exception as e:
            sublime.message_dialog('Upload error: %s' % e)


class MediawikerFavoritesAddCommand(sublime_plugin.WindowCommand):

    def run(self):
        title = mw_get_title()
        mw_save_mypages(title=title, storage_name='mediawiker_favorites')


class MediawikerFavoritesOpenCommand(sublime_plugin.WindowCommand):

    def run(self):
        self.window.run_command("mediawiker_page_list", {"storage_name": 'mediawiker_favorites'})
