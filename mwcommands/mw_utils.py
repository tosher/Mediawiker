#!/usr/bin/env python\n
# -*- coding: utf-8 -*-

import sys

import os
import re
import urllib
import traceback

try:
    from collections import OrderedDict
except ImportError:
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
    import base64
    from . import mw_properties as mwprops
    from . import mw_parser as par
    from html.parser import HTMLParser
    from ..lib import mwclient
    from ..lib import browser_cookie3
else:
    import mw_properties as mwprops
    from HTMLParser import HTMLParser
    from lib import mwclient


# linting skips
# all must be ovverrided in plugin_loaded

def get_setting(key, default_value=None):
    pass


def set_setting(key, value):
    pass


def del_setting(key):
    pass


def get_default_setting(key, default_value=None):
    pass


def from_package(*path):
    pass


conman = None
api = None
props = None


def plugin_loaded():
    mw = sys.modules[__name__]
    props = mwprops.MediawikerProperties()
    setattr(mw, 'props', props)

    for attr in dir(mwprops):
        if isinstance(getattr(mwprops, attr), (str, int)) and not attr.startswith('_'):
            setattr(mw, attr, getattr(mwprops, attr))

    setattr(mw, 'from_package', mwprops.from_package)
    setattr(mw, 'get_setting', props.get_setting)
    setattr(mw, 'set_setting', props.set_setting)
    setattr(mw, 'del_setting', props.del_setting)
    setattr(mw, 'get_default_setting', props.get_default_setting)

    if not mw.props.get_setting('offline_mode'):
        conman = MediawikerConnectionManager()
        setattr(mw, 'conman', conman)
        setattr(mw, 'api', PreAPI(conman=conman))


def set_syntax(page_name=None, page_namespace=None):
    syntax = get_setting('syntax')

    if page_name and page_namespace:
        syntax_ext = 'sublime-syntax' if int(sublime.version()) >= 3084 else 'tmLanguage'

        # Scribunto lua modules, except doc subpage
        if page_namespace == api.SCRIBUNTO_NAMESPACE and not page_name.lower().endswith('/doc'):
            syntax = from_package('Lua.%s' % syntax_ext, name='Lua')
        elif page_name.lower().endswith('.css'):
            syntax = from_package('CSS.%s' % syntax_ext, name='CSS')
        elif page_name.endswith('.js'):
            syntax = from_package('Javascript.%s' % syntax_ext, name='Javascript')

    sublime.active_window().active_view().set_syntax_file(syntax)


def cmd(cmd):
    if cmd.startswith(mwprops.PML):
        return cmd
    else:
        return '_'.join([mwprops.PML, cmd])


def get_view_site():
    try:
        return props.get_view_setting(sublime.active_window().active_view(), 'site', get_setting('site_active'))
    except:
        # st2 exception on start.. sublime not available on activated..
        return get_setting('site_active')


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
            wiki_extensions = get_setting('files_extension')
            title, ext = os.path.splitext(os.path.basename(file_name))
            if ext[1:] in wiki_extensions and title:
                return title
            else:
                status_message('Unauthorized file extension for mediawiki publishing. Check your configuration for correct extensions.')
                return ''
    return ''


def show_red_links(view, page):
    set_timeout_async(process_red_links(view, page), 0)


def process_red_links(view, page):

    # ST2 hasn't phantoms
    if pythonver < 3:
        status_message('Commands "Show red links/Hide red links" supported in Sublime text 3 only.')
        return

    status_message('Processing red_links for page [[%s]].. ' % api.page_attr(page, 'name'), new_line=False)

    view.erase_phantoms('redlink')
    red_link_icon = get_setting('red_link_icon')
    linksgen = api.get_page_links(page, generator=True)

    links_d = {}
    for link in linksgen:
        if link.namespace not in links_d:
            links_d[link.namespace] = {}
            links_d[link.namespace]['names'] = []
            links_d[link.namespace]['data'] = []
        links_d[link.namespace]['names'].append(link.page_title)
        links_d[link.namespace]['data'].append(link)

    p = par.Parser(view)
    p.register_all(par.Comment, par.Link, par.Pre, par.Source)
    if not p.parse():
        return

    links = p.links

    for l in links:
        l_ns_number = api.get_namespace_number(l.namespace)
        l_name = l.get_titled(l.get_spaced(l.title))
        if l_ns_number in links_d and l_name in links_d[l_ns_number]['names']:
            idx = links_d[l_ns_number]['names'].index(l_name)
            link = links_d[l_ns_number]['data'][idx]
            if not link.exists:
                view.add_phantom(
                    'redlink',
                    sublime.Region(l.region.a + 2, l.region.a + 2),
                    '<strong style="padding: 0px; color: #c0392b;">%s</strong>' % red_link_icon,
                    sublime.LAYOUT_INLINE
                )
    status_message('done.')


def pagename_clear(pagename):
    """ Return clear pagename if page-url was set instead of.."""
    site = get_setting('site').get(get_view_site())
    host = site.get('host', None)
    pagepath = site.get('pagepath', None)

    if not host or not pagepath:
        return pagename

    try:
        pagename = strunquote(pagename)
    except UnicodeEncodeError:
        pass
    except Exception:
        pass

    if host in pagename:
        pagename = re.sub(r'(https?://)?%s%s' % (host, pagepath), '', pagename)

    return pagename


def save_mypages(title, storage_name='pagelist'):

    title = title.replace('_', ' ')  # for wiki '_' and ' ' are equal in page name
    pagelist_maxsize = get_setting('pagelist_maxsize')
    site_active = get_view_site()
    pagelist = get_setting(storage_name, {})

    if site_active not in pagelist:
        pagelist[site_active] = []

    my_pages = pagelist[site_active]

    if my_pages:
        while len(my_pages) >= pagelist_maxsize:
            my_pages.pop(0)

        if title in my_pages:
            # for sorting
            my_pages.remove(title)
    my_pages.append(title)
    set_setting(storage_name, pagelist)


def get_hlevel(header_string, substring):
    return int(header_string.count(substring) / 2)


def get_category(category_full_name):
    ''' From full category name like "Category:Name" return tuple (Category, Name) '''
    if ':' in category_full_name:
        return category_full_name.split(':')
    else:
        return 'Category', category_full_name


def get_page_url(page_name=None):

    if page_name is None:
        page_name = strquote(get_title())

    site = get_setting('site').get(get_view_site())
    host = site['host']
    proto = 'https' if site.get('https', True) else 'http'
    pagepath = site.get("pagepath", '/wiki/')

    if page_name:
        return '%s://%s%s%s' % (proto, host, pagepath, page_name)

    return ''


def status_message(message, replace=None, is_panel=None, new_line=True, panel_name=None, syntax=None, new=False):

    def status_message_sublime(message, replace=None):
        if replace:
            for r in replace:
                message = message.replace(r, '')
        sublime.status_message(message)

    is_use_message_panel = is_panel if is_panel is not None else get_setting('use_status_messages_panel', True)

    if is_use_message_panel:
        panel = None
        if panel_name is None:
            panel_name = '%s_panel' % mwprops.PML

        if syntax is None:
            if int(sublime.version()) >= 3000:
                syntax = from_package('MediawikerPanel.sublime-syntax')
            else:
                syntax = from_package('MediawikiNG_ST2.tmLanguage')

        if int(sublime.version()) >= 3000:
            if not new:
                panel = sublime.active_window().find_output_panel(panel_name)

            if panel is None:
                panel = sublime.active_window().create_output_panel(panel_name)

        else:
            panel = sublime.active_window().get_output_panel(panel_name)

        if panel is not None:
            panel.set_syntax_file(syntax)
            sublime.active_window().run_command("show_panel", {"panel": "output.%s" % panel_name})
            props.set_view_setting(panel, 'is_here', True)
            panel.set_read_only(False)
            last_position = panel.size()
            panel.run_command(cmd('insert_text'), {'position': panel.size(), 'text': '%s%s' % (message, '\n' if new_line else '')})
            panel.show_at_center(last_position)
            panel.set_read_only(True)

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

    CATEGORY_NAMESPACE = 14
    IMAGE_NAMESPACE = 6
    TEMPLATE_NAMESPACE = 10
    SCRIBUNTO_NAMESPACE = 828
    USER_NAMESPACE = 2
    MEDIAWIKI_NAMESPACE = 8
    PROJECT_NAMESPACE = 4
    SCRIBUNTO_PREFIX = '#invoke'
    NAMESPACE_SPLITTER = u':'
    INTERNAL_LINK_SPLITTER = u'|'
    PAGE_CANNOT_READ_MESSAGE = 'You have not rights to read/edit this page.'
    PAGE_CANNOT_EDIT_MESSAGE = 'You have not rights to edit this page.'

    def __init__(self, conman):
        self.conman = conman

    def get_connect(self, force=False):
        sitecon = self.conman.get_connect(force=force)

        if sitecon and (not hasattr(sitecon, 'logged_in') or not sitecon.logged_in):
            status_message('Anonymous connection detected, forcing new connection.. ')
            sitecon = self.conman.get_connect(force=True)

        if not sitecon and get_setting('offline_mode'):
            raise ConnectionFailed("Connection not available in offline mode")
        if not sitecon:
            raise ConnectionFailed("No valid connection available")
        return sitecon

    def call(self, func, **kwargs):

        if not isinstance(func, str):
            status_message('Error: PreAPI call arg must be a string, not %s.' % type(func))
            return

        try:
            funcobj = getattr(self, func)
        except AttributeError as e:
            status_message('PreAPI %s error in %s: %s' % (type(e).__name__, func, e))
            return

        if funcobj:
            while True:
                try:
                    return funcobj(**kwargs)
                except mwclient.errors.APIError as e:
                    status_message("%s exception for %s: %s, trying to reconnect.. " % (type(e).__name__, func, e))
                    try:
                        status_message('Forcing new connection.. ')
                        _ = self.get_connect(force=True)  # one time try to reconnect
                        if _:
                            return funcobj(**kwargs)
                        else:
                            status_message('Failed to call %s' % funcobj.__name__)  # TODO: check
                            break
                    except Exception as e:
                        status_message("%s exception for %s: %s" % (type(e).__name__, func, e))
                        break
                except Exception as e:
                    status_message("%s exception for %s: %s" % (type(e).__name__, func, e))
                    break

    def get_page(self, title):
        return self.get_connect().Pages.get(title, None)

    def page_move(self, page, new_title, reason='', no_redirect=False):
        result = page.move(new_title=new_title, reason=reason, move_talk=True, no_redirect=no_redirect)
        return result

    def image_init(self, name, extra_properties):
        return mwclient.Image(site=self.get_connect(), name=name, extra_properties=extra_properties)

    def get_image(self, title, thumb=True, thumb_size=100, url=False):
        '''
        thumb: return thumb or full-size image (False not implemeted now)
        thumb_size: max thumb size to return
        url: return image url or base64 data ("http:" is not works: https://github.com/SublimeTextIssues/Core/issues/1378)
        '''

        page = self.get_page(title)  # use image?
        if self.page_attr(page, 'namespace') == self.IMAGE_NAMESPACE:
            # Link like [[File:Filename]] has not imageinfo, only [[Image:Imagename]]
            if not hasattr(page, 'imageinfo'):
                page = self.get_page('Image:%s' % self.page_attr(page, 'page_title'))
            img_width = page.imageinfo.get('width', thumb_size)
            img_url = page.imageinfo.get('url', thumb_size)
            img_size_request = min(img_width, thumb_size)
            extra_properties = {
                'imageinfo': (
                    ('iiprop', 'timestamp|user|comment|url|size|sha1|metadata|archivename'),
                    ('iiurlwidth', img_size_request)
                )
            }
            img = self.call('image_init', name=title, extra_properties=extra_properties)
            img_thumb_url = img.imageinfo.get('thumburl', None)
            if img_thumb_url is not None:
                response = requests.get(img_thumb_url)
                img_base64 = "data:" + response.headers['Content-Type'] + ";" + "base64," + str(base64.b64encode(response.content).decode("utf-8"))
                return (img_base64, img_size_request, img_url)
        return None

    def get_page_backlinks(self, page, limit):
        return page.backlinks(limit=limit)

    def get_page_embeddedin(self, page, limit):
        return page.embeddedin(limit=limit)

    def get_page_links(self, page, generator=True, namespace=None):

        def add(arr, gen):
            for g in gen:
                arr.append(g)
            return arr

        links = page.links(generator=generator)
        images = page.images(generator=generator)
        categories = page.categories(generator=generator)
        templates = page.templates(generator=generator)

        links_all = []
        add(links_all, links)
        add(links_all, images)
        add(links_all, categories)
        add(links_all, templates)

        return links_all

    def get_page_talk_page(self, page):
        ns = self.page_attr(page, 'namespace')
        title = self.page_attr(page, 'page_title')

        if ns == self.CATEGORY_NAMESPACE:
            return self.get_page('Category_talk:%s' % title)
        elif ns == self.IMAGE_NAMESPACE:
            return self.get_page('File_talk:%s' % title)
        elif ns == self.TEMPLATE_NAMESPACE:
            return self.get_page('Template_talk:%s' % title)
        elif ns == self.SCRIBUNTO_NAMESPACE:
            return self.get_page('Module_talk:%s' % title)
        elif ns == self.USER_NAMESPACE:
            return self.get_page('User_talk:%s' % title)
        elif ns == self.MEDIAWIKI_NAMESPACE:
            return self.get_page('Mediawiki_talk:%s' % title)
        elif ns == self.PROJECT_NAMESPACE:
            return self.get_page('Project_talk:%s' % title)
        return self.get_page('Talk:%s' % title)

    def get_page_extlinks(self, page):
        return [l for l in page.extlinks()]

    def get_page_langlinks(self, page):
        return page.langlinks()

    def save_page(self, page, text, summary, mark_as_minor):
        try:
            # verify connection
            self.get_connect()
        except Exception as e:
            status_message('%s exception: %s' % (type(e).__name__, e))

        try:
            page.save(text, summary=summary.strip(), minor=mark_as_minor)
        except Exception as e:
            status_message('%s exception: %s' % (type(e).__name__, e))

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
        return self.get_connect().Categories.get(category_root, [])

    def get_pages(self, prefix, namespace):
        return self.get_connect().allpages(prefix=prefix, namespace=namespace)

    def get_notifications(self):
        return self.get_connect().notifications()

    def get_notifications_list(self, ignore_read=False):

        def msg_data(msg):
            m = {}
            m['title'] = msg.get('title', {}).get('full')
            m['type'] = msg.get('type', None)
            m['timestamp'] = msg.get('timestamp', {}).get('date', None)
            m['agent'] = msg.get('agent', {}).get('name', None)
            m['read'] = True if msg.get('read', False) else False
            return m

        ns = self.call('get_notifications')
        msgs = []
        if ns:
            if isinstance(ns, dict):
                for n in ns.keys():
                    msg = ns.get(n, {})
                    msg_read = msg.get('read', False)
                    if not msg_read or not ignore_read:
                        msgs.append(msg_data(msg))
            elif isinstance(ns, list):
                for msg in ns:
                    msg_read = msg.get('read', False)
                    if not msg_read or not ignore_read:
                        msgs.append(msg_data(msg))
        return msgs

    def exists_unread_notifications(self):
        ns = self.call('get_notifications')
        if ns:
            if isinstance(ns, dict):
                for n in ns.keys():
                    msg = ns.get(n, {})
                    msg_read = msg.get('read', None)
                    if not msg_read:
                        return True
            elif isinstance(ns, list):
                for msg in ns:
                    msg_read = msg.get('read', None)
                    if not msg_read:
                        return True
        return False

    def get_parse_result(self, text, title):
        return self.get_connect().parse(text=text, title=title, disableeditsection=True).get('text', {}).get('*', '')

    def get_search_result(self, search, limit, namespace):
        return self.get_connect().search(search=search, what='text', limit=limit, namespace=namespace)

    def process_upload(self, file_handler, filename, description):
        return self.get_connect().upload(file_handler, filename, description)

    def get_namespace_number(self, name):
        if name is None:
            return 0

        sitecon = self.get_connect()
        return sitecon.namespaces_canonical_invert.get(
            name, sitecon.namespaces_invert.get(
                name, sitecon.namespaces_aliases_invert.get(
                    name, None)))

    def is_equal_ns(self, ns_name1, ns_name2):
        ns_name1_number = self.get_namespace_number(name=ns_name1)
        ns_name2_number = self.get_namespace_number(name=ns_name2)
        if ns_name1_number and ns_name2_number and int(ns_name1_number) == int(ns_name2_number):
            return True
        return False


class MediawikerConnectionManager(object):

    AUTH_TYPE_LOGIN = 'login'
    AUTH_TYPE_OAUTH = 'oauth'
    AUTH_TYPE_COOKIES = 'cookies'

    def __init__(self):
        self.sites = {}
        self.debug_msgs = []

    def get_site_config(self, name):
        ''' get site settings '''
        site_config = get_setting('site').get(name)
        self.validate_site(name, site_config)

    def is_site_changed(self, oldsite, newsite):
        if not oldsite and newsite:
            return True

        return oldsite != newsite

    def validate_site(self, name, site_config):
        ''' validate and update site configuration
            drops connection if site configuration was changed
        '''

        def get_proto():
            return 'https' if site['https'] else 'http'

        assert 'host' in site_config, 'Host is not defined for site %s' % name

        site = self.sites.get(name, {})
        site_config_old = site.get('config', {})

        if self.is_site_changed(site_config_old, site_config):
            if not site_config_old:
                status_message("'''Setup new connection to \"%s\".'''" % name)
            else:
                status_message("'''Site configuration is changed, setup new connection to \"%s\".. '''" % name)
            if 'connection' in site:
                site['connection'] = None

            site['config'] = site_config
            site['host'] = site_config['host']
            site['username'] = site_config.get('username', None)
            site['password'] = site_config.get('password', None) or site.get('password', None)
            site['domain'] = site_config.get('domain', None)
            site['path'] = site_config.get('path', '/w/')
            site['pagepath'] = site_config.get('pagepath', '/wiki/')
            site['authorization_type'] = site_config.get('authorization_type', self.AUTH_TYPE_LOGIN)
            site['cookies_browser'] = site_config.get('cookies_browser', 'chrome') if site['authorization_type'] == self.AUTH_TYPE_COOKIES else None
            site['https'] = site_config.get('https', True)
            site['hosturl'] = (get_proto(), site['host'])
            site['is_ssl_cert_verify'] = site_config.get('is_ssl_cert_verify', True)
            site['retry_timeout'] = site_config.get('retry_timeout', 30)
            site['proxy_host'] = site_config.get('proxy_host', None)
            site['proxies'] = {get_proto(): site['proxy_host']} if site['proxy_host'] else None
            site['cookies'] = None
            site['use_http_auth'] = site_config.get('use_http_auth', False)
            site['http_auth_login'] = site_config.get('http_auth_login', None)
            site['http_auth_password'] = site_config.get('http_auth_password', None)
            site['oauth_consumer_token'] = site_config.get('oauth_consumer_token', None)
            site['oauth_consumer_secret'] = site_config.get('oauth_consumer_secret', None)
            site['oauth_access_token'] = site_config.get('oauth_access_token', None)
            site['oauth_access_secret'] = site_config.get('oauth_access_secret', None)
            site['preview_custom_head'] = site_config.get('preview_custom_head', None)

            self.sites[name] = site

    def get_site(self, name=None):
        ''' returns actual site options, includes connection '''

        if name is None:
            name = get_view_site()

        self.get_site_config(name=name)

        return self.sites.get(name, None)

    def update_site(self, name=None, **options):
        ''' update site settings
            * add/update connection
            * add/update password
        '''
        site = self.get_site(name)
        for key in options.keys():
            site[key] = options[key]

    def get_requests_config(self, name=None):
        site = self.get_site(name)

        # proxies:
        #   proxy host like: http(s)://user:pass@10.10.1.10:3128
        #   Note: PC uses requests ver. 2.7.0. Per-host proxies supported from 2.8.0 version only.
        #   http://docs.python-requests.org/en/latest/community/updates/#id4
        #   host_key = '%s://%s' % ('https' if self.is_https else 'http', self.site)
        #   using proto only..

        return {
            'verify': site['is_ssl_cert_verify'],
            'proxies': site['proxies'],
            'timeout': (site['retry_timeout'], None)
        }

    def debug_flush(self):
        if get_setting('debug'):
            for msg in self.debug_msgs:
                status_message("'''DEBUG''' %s" % msg)
        self.debug_msgs = []

    def get_connect(self, name=None, force=False):
        ''' setup new connection (call connect()) or returns exists '''

        if get_setting('offline_mode'):
            return None

        self.debug_msgs.append('Get connection from connection manager.')
        try:
            site = self.get_site(name)

            cj = self.get_cookies(name=name) if site['authorization_type'] == self.AUTH_TYPE_COOKIES else None

            if site['authorization_type'] == self.AUTH_TYPE_COOKIES and not self.is_eq_cookies(site['cookies'], cj):
                self.debug_msgs.append('New cookies: %s' % cj)
                site['cookies'] = cj
            elif not force and (site['authorization_type'] != self.AUTH_TYPE_LOGIN or not site['username'] or site['password']):
                connection = site.get('connection', None)

                if connection:
                    self.debug_msgs.append('Cached connection: True')
                    self.debug_flush()
                    return connection

        except Exception as e:
            formatted_lines = traceback.format_exc().splitlines()
            for line in formatted_lines:
                status_message(line)

        try:
            connection = self.connect(name=name)
        except Exception as e:
            self.debug_msgs.append('Connection exception: %s' % e)

        self.debug_flush()

        return connection

    def connect(self, name=None):
        ''' new connection '''

        site = self.get_site(name)

        status_message('Connecting to %s .. ' % self.url(name), new_line=False)

        if site['authorization_type'] == self.AUTH_TYPE_OAUTH:
            # oauth authorization
            connection = self._oauth()
        else:
            # Site connection
            try:
                connection = mwclient.Site(
                    host=site['hosturl'],
                    path=site['path'],
                    retry_timeout=None,
                    max_retries=None,
                    requests=self.get_requests_config(name)
                )
            except requests.exceptions.HTTPError as e:
                if get_setting('debug'):
                    self.debug_msgs.append('HTTP response: %s' % e)

                # additional http auth (basic, digest)
                if e.response.status_code == 401 and site['use_http_auth']:
                    http_auth_header = e.response.headers.get('www-authenticate', '')
                    connection = self._http_auth(http_auth_header=http_auth_header, name=name)
                else:
                    # sublime.message_dialog('HTTP connection failed: %s' % e[1])
                    status_message(' failed: %s' % e[1])
                    return
            except Exception as e:
                # sublime.message_dialog('Connection failed for %s: %s' % (site['hosturl'], e))
                status_message(' failed: %s' % e)
                return

        if connection:
            status_message(' done.')
            if get_setting('debug'):
                self.debug_msgs.append('Connection: %s' % connection.connection)

            status_message('Login in with authorization type %s.. ' % site['authorization_type'], new_line=False)
            success_message = ' done'
            # Cookie auth
            if site['authorization_type'] == self.AUTH_TYPE_COOKIES and site['cookies']:
                try:
                    connection.login(cookies=site['cookies'])

                    if get_setting('debug'):
                        self.debug_msgs.append('Username: %s' % connection.username.strip())
                        # not connection.logged_in and self.debug_msgs.append('* Anonymous connection: True')
                        self.debug_msgs.append('Anonymous connection: True') if not connection.logged_in else None
                        self.debug_msgs.append('Connection rights: %s' % (', '.join(connection.rights)))
                        self.debug_msgs.append('Connection tokens: %s' % (', '.join(['%s: %s' % (
                            t,
                            connection.tokens[t]
                        ) for t in connection.tokens.keys()]) if connection.tokens else '<empty>'))

                except mwclient.LoginError as exc:
                    e = exc.args if pythonver >= 3 else exc
                    status_message(' failed: %s' % e[1]['result'])
                    return
            # Login/Password auth
            elif site['authorization_type'] == self.AUTH_TYPE_LOGIN and site['username'] and site['password']:
                try:
                    connection.login(username=site['username'], password=site['password'], domain=site['domain'])
                except mwclient.LoginError as exc:
                    e = exc.args if pythonver >= 3 else exc
                    status_message(' failed: %s' % e[1]['result'])
                    return
            # elif self.auth_type == self.AUTH_TYPE_OAUTH:
            else:
                success_message = ' done, without authorization.'  # TODO: recheck AUTH messages

            status_message(success_message)

            site['connection'] = connection
            return connection
        else:
            status_message(' failed.')

        return None

    def require_password(self, name=None):

        site = self.get_site(name)
        if site['authorization_type'] == self.AUTH_TYPE_LOGIN and not site.get('password', None):
            return True
        return False

    def url(self, name=None):
        site = self.get_site(name)
        return ''.join([site['hosturl'][0], '://', site['hosturl'][1]])

    def get_cookies(self, name):
        site = self.get_site(name)

        if site['authorization_type'] != self.AUTH_TYPE_COOKIES:
            return None

        cookie_files = get_setting('%s_cookie_files' % site['cookies_browser'], [])
        if not cookie_files:
            cookie_files = None

        if site['cookies_browser'] == "firefox":
            return browser_cookie3.firefox(cookie_files=cookie_files, domain_name=site['host'], copy_path=from_package(name='User', posix=True, is_abs=True))
        elif site['cookies_browser'] == 'chrome':
            return browser_cookie3.chrome(cookie_files=cookie_files, domain_name=site['host'])
        else:
            sublime.message_dialog("Incompatible browser for cookie: %s" % (site['cookies_browser'] or "Not defined"))

        return None

    def is_eq_cookies(self, cj1, cj2):
        cj1_set = set((c.domain, c.path, c.name, c.value) for c in cj1) if cj1 else set()
        cj2_set = set((c.domain, c.path, c.name, c.value) for c in cj2) if cj2 else set()
        return not bool(cj1_set - cj2_set or cj2_set - cj1_set)

    def _http_auth(self, http_auth_header, name=None):
        DIGEST_REALM = 'Digest realm'
        BASIC_REALM = 'Basic realm'

        site = self.get_site(name)

        http_auth_login = site['http_auth_login']
        http_auth_password = site['http_auth_password']

        if not http_auth_login or not http_auth_password:
            return None

        httpauth = None
        realm = None
        if http_auth_header.startswith(BASIC_REALM):
            realm = BASIC_REALM
        elif http_auth_header.startswith(DIGEST_REALM):
            realm = DIGEST_REALM

        if realm is not None:
            if realm == BASIC_REALM:
                httpauth = requests.auth.HTTPBasicAuth(http_auth_login, http_auth_password)
            elif realm == DIGEST_REALM:
                httpauth = requests.auth.HTTPDigestAuth(http_auth_login, http_auth_password)

            if httpauth:
                connection = mwclient.Site(
                    host=site['hosturl'],
                    path=site['path'],
                    httpauth=httpauth,
                    requests=self.get_requests_config(name))
                return connection
        else:
            status_message('HTTP connection failed: Unknown realm.')

        return None

    def _oauth(self, name=None):

        site = self.get_site(name)

        if site['authorization_type'] != self.AUTH_TYPE_OAUTH:
            return None

        if all([
            site['oauth_consumer_token'],
            site['oauth_consumer_secret'],
            site['oauth_access_token'],
            site['oauth_access_secret']
        ]):
            try:
                connection = mwclient.Site(
                    host=self.hosturl,
                    path=self.path,
                    retry_timeout=None,
                    max_retries=None,
                    consumer_token=site['oauth_consumer_token'],
                    consumer_secret=site['oauth_consumer_secret'],
                    access_token=site['oauth_access_token'],
                    access_secret=site['oauth_access_secret'],
                    requests=self.get_requests_config(name)
                )
                return connection
            except mwclient.OAuthAuthorizationError as exc:
                e = exc.args if pythonver >= 3 else exc
                status_message('OAuth login failed: %s' % e[1])
        return None


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
            if bool(get_setting('clipboard_as_defaultpagename')):
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
        site = conman.get_site()

        if site['authorization_type'] != conman.AUTH_TYPE_LOGIN:
            self.on_done(password=None)
            return

        password = site['password']
        if site['username']:
            # auth required if username exists in settings
            if not password:
                self.is_hide_password = get_setting('password_input_hide')
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
            conman.update_site(password=password)
        set_timeout_async(self.callback, 0)


class PasswordHider(object):

    password = ''

    def hide(self, password):
        password_char = get_setting('password_char', '*')
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
            for p in self.params.keys():
                param = '%s=%s' % (p, self.params[p])
                params_list.append(param)
        return params_list


if pythonver < 3:
    plugin_loaded()

