#!/usr/bin/env python\n
# -*- coding: utf-8 -*-

import sys
import os
import re
import urllib
# import traceback
from collections import OrderedDict

import sublime
# import sublime_plugin
import requests

# NOTE: load from package, not used now because custom ssl
# current_dir = dirname(__file__)
# if '.sublime-package' in current_dir:
#     sys.path.append(current_dir)
#     import mwclient
# else:
#     from . import mwclient
import base64
from . import mw_properties as p
from . import mw_parser as par
from html.parser import HTMLParser
from ..lib import mwclient

from ..lib import browser_cookie3

conman = None
api = None
props = None

NS_SEARCH_DISABLED = 'disabled'

# def plugin_loaded():
#     mw = sys.modules[__name__]
#     props = p.MediawikerProperties()
#     setattr(mw, 'props', props)

#     for attr in dir(mw_properties):
#         if isinstance(getattr(mw_properties, attr), (str, int)) and not attr.startswith('_'):
#             setattr(mw, attr, getattr(mw_properties, attr))

#     setattr(mw, 'from_package', mw_properties.from_package)
#     setattr(mw, 'get_setting', props.get_setting)
#     setattr(mw, 'set_setting', props.set_setting)
#     setattr(mw, 'del_setting', props.del_setting)
#     setattr(mw, 'get_default_setting', props.get_default_setting)

#     if not mw.props.get_setting('offline_mode'):
#         conman = MediawikerConnectionManager()
#         setattr(mw, 'conman', conman)
#         setattr(mw, 'api', PreAPI(conman=conman))


def plugin_loaded():
    props = p.MediawikerProperties()
    conman = MediawikerConnectionManager()
    api = PreAPI(conman=conman)
    mw = sys.modules[__name__]
    setattr(mw, 'props', props)
    setattr(mw, 'conman', conman)
    setattr(mw, 'api', api)


def get_syntax_property(page_name=None, page_namespace=None):
    if page_name and page_namespace:
        if page_namespace == api.SCRIBUNTO_NAMESPACE and not page_name.lower().endswith('/doc'):
            # Scribunto lua modules, except doc subpage
            return 'syntax_lua'
        elif page_name.lower().endswith('.css'):
            return 'syntax_css'
        elif page_name.lower().endswith('.js'):
            return 'syntax_js'
    return 'syntax'


def set_syntax(page_name=None, page_namespace=None):
    syntax_prop = get_syntax_property(page_name, page_namespace)
    sublime.active_window().active_view().set_syntax_file(props.get_setting(syntax_prop))


def get_view_syntax(view):
    return view.settings().get('syntax')


def comment(text, page_name=None, page_namespace=None):
    syntax_formats = {
        'syntax_lua': '-- {}',
        'syntax_css': '/* {} */',
        'syntax_js': '// {}',
        'syntax': '<!-- {} -->'
    }
    syntax_prop = get_syntax_property(page_name, page_namespace)
    if syntax_formats.get(syntax_prop):
        return syntax_formats[syntax_prop].format(text)
    return syntax_formats['syntax'].format(text)


def cmd(cmd):
    if cmd.startswith(p.PML):
        return cmd
    else:
        return '_'.join([p.PML, cmd])


def get_view_site():
    try:
        return props.get_view_setting(sublime.active_window().active_view(), 'site', props.get_setting('site_active'))
    except Exception:
        # st2 exception on start.. sublime not available on activated..
        return props.get_setting('site_active')


def enco(value):
    ''' for md5 hashing string must be encoded '''
    return value.encode('utf-8')


def deco(value):
    ''' for py3 decode from bytes '''
    return value.decode('utf-8')


def strunquote(string_value):
    return urllib.parse.unquote(string_value)


def strquote(string_value):
    return urllib.parse.quote(string_value)


def get_title():
    ''' returns page title of active tab from view_name or from file_name'''

    view_name = sublime.active_window().active_view().name()
    if view_name:
        return view_name
    else:
        # haven't view.name, try to get from view.file_name (without extension)
        file_name = sublime.active_window().active_view().file_name()
        if file_name:
            wiki_extensions = props.get_setting('files_extension')
            title, ext = os.path.splitext(os.path.basename(file_name))
            if ext[1:] in wiki_extensions and title:
                return title
            else:
                error_message('Unauthorized file extension for mediawiki publishing. Check your configuration for correct extensions.')
                return ''
    return ''


def show_red_links(view, page):
    set_timeout_async(process_red_links(view, page), 0)


def process_red_links(view, page):
    status_message('Processing red_links for page [[{}]].. '.format(api.page_attr(page, 'name')), new_line=False)

    view.erase_phantoms('redlink')
    red_link_icon = props.get_setting('red_link_icon')
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
    p.register_all(par.Comment, par.Link, par.Pre, par.Source, par.Nowiki)
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
                    '<strong style="padding: 0px; color: #c0392b;">{}</strong>'.format(red_link_icon),
                    sublime.LAYOUT_INLINE
                )
    status_message('done.')


def pagename_clear(pagename):
    """ Return clear pagename if page-url was set instead of.."""
    site = get_view_site()
    host = props.get_site_setting(site, 'host')
    pagepath = props.get_site_setting(site, 'pagepath')

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
    pagelist_maxsize = props.get_setting('pagelist_maxsize')
    site_active = get_view_site()
    pagelist = props.get_setting(storage_name, {})

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
    props.set_setting(storage_name, pagelist)


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

    site = props.get_site(get_view_site())
    host = site['host']
    proto = 'https' if site.get('https', True) else 'http'
    pagepath = site.get('pagepath', '/wiki/')

    if page_name:
        return '{}://{}{}{}'.format(proto, host, pagepath, page_name)

    return ''


def get_search_ns():
    '''
    Returns 'search_namespaces':
    * if defined on site level, then site-level-namespaces
    * if magic word NS_SEARCH_DISABLED (const) defined as value on site level, returns None
    * else global option
    '''

    nses = props.get_site_setting(get_view_site(), 'search_namespaces')
    # we can disable search on site level
    # * slow page completions, etc
    if nses == NS_SEARCH_DISABLED:
        return None

    if not nses:
        nses = props.get_setting('search_namespaces')

    return [ns.strip() for ns in nses.split(',')]


def status_message(message, replace_patterns=None, is_panel=None, new_line=True, panel_name=None, syntax=None, new=False):

    def status_message_sublime(message, replace_patterns=None):
        if replace_patterns:
            for rp in replace_patterns:
                message = message.replace(rp, '')
        sublime.active_window().status_message(message)

    if is_panel is None:
        is_panel = False
        if props.get_setting('use_panel_on_success', True):
            is_panel = True

    if not is_panel:
        status_message_sublime(message, replace_patterns)
        return

    panel = None
    if panel_name is None:
        panel_name = '{}_panel'.format(p.PML)

    if syntax is None:
        syntax = p.from_package('MediawikerPanel.sublime-syntax')

    if not new:
        panel = sublime.active_window().find_output_panel(panel_name)

    if panel is None:
        panel = sublime.active_window().create_output_panel(panel_name)

    if panel is not None:
        panel.set_syntax_file(syntax)
        sublime.active_window().run_command("show_panel", {"panel": "output.{}".format(panel_name)})
        props.set_view_setting(panel, 'is_here', True)
        panel.set_read_only(False)
        last_position = panel.size()
        panel.run_command(cmd('insert_text'), {'position': panel.size(), 'text': '{}{}'.format(message, '\n' if new_line else '')})
        panel.show_at_center(last_position)
        panel.set_read_only(True)

    else:
        status_message_sublime(message, replace_patterns)


def error_message(message, replace_patterns=None, is_panel=None, new_line=True, panel_name=None, syntax=None, new=False):
    if is_panel or props.get_setting('use_panel_on_error', True):
        is_panel = True
    message = ' '.join(['  >>>', message])
    status_message(message, replace_patterns, is_panel, new_line, panel_name, syntax, new)


def set_timeout_async(callback, delay):
    sublime.set_timeout_async(callback, delay)


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
    UPLOAD_SUCCESS = 'Success'

    def __init__(self, conman, site_name=None):
        self.conman = conman
        self.site_name = site_name

    def get_connect(self, force=False):
        sitecon = self.conman.get_connect(name=self.site_name, force=force)

        if sitecon and (not hasattr(sitecon, 'logged_in') or not sitecon.logged_in):
            status_message('Anonymous connection detected, forcing new connection.. ')
            sitecon = self.conman.get_connect(name=self.site_name, force=True)

        if not sitecon and props.get_setting('offline_mode'):
            raise ConnectionFailed("Connection not available in offline mode")
        if not sitecon:
            raise ConnectionFailed("No valid connection available")
        return sitecon

    def call(self, func, **kwargs):

        if not isinstance(func, str):
            error_message('Error: PreAPI call arg must be a string, not {}.'.format(type(func)))
            return

        try:
            funcobj = getattr(self, func)
        except AttributeError as e:
            error_message('PreAPI {} error in {}: {}'.format(type(e).__name__, func, e))
            return

        if funcobj:
            while True:
                try:
                    return funcobj(**kwargs)
                except mwclient.errors.APIError as e:
                    error_message("{} exception for {}: {}, trying to reconnect.. ".format(type(e).__name__, func, e))
                    try:
                        error_message('Forcing new connection.. ')
                        _ = self.get_connect(force=True)  # one time try to reconnect
                        if _:
                            return funcobj(**kwargs)
                        else:
                            error_message('Failed to call {}'.format(funcobj.__name__))  # TODO: check
                            break
                    except Exception as e:
                        error_message("{} exception for {}: {}".format(type(e).__name__, func, e))
                        break
                except Exception as e:
                    error_message("{} exception for {}: {}".format(type(e).__name__, func, e))
                    break

    def get_page(self, title):
        try:
            return self.get_connect().Pages.get(title, None)
        except Exception as e:
            error_message('Unable to get page "{}", {} exception raised: {}'.format(title, type(e).__name__, e))

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
                page = self.get_page('Image:{}'.format(self.page_attr(page, 'page_title')))
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
            return self.get_page('Category_talk:{}'.format(title))
        elif ns == self.IMAGE_NAMESPACE:
            return self.get_page('File_talk:{}'.format(title))
        elif ns == self.TEMPLATE_NAMESPACE:
            return self.get_page('Template_talk:{}'.format(title))
        elif ns == self.SCRIBUNTO_NAMESPACE:
            return self.get_page('Module_talk:{}'.format(title))
        elif ns == self.USER_NAMESPACE:
            return self.get_page('User_talk:{}'.format(title))
        elif ns == self.MEDIAWIKI_NAMESPACE:
            return self.get_page('Mediawiki_talk:{}'.format(title))
        elif ns == self.PROJECT_NAMESPACE:
            return self.get_page('Project_talk:{}'.format(title))
        return self.get_page('Talk:{}'.format(title))

    def get_page_extlinks(self, page):
        return [link for link in page.extlinks()]

    def get_page_langlinks(self, page):
        return page.langlinks()

    def save_page(self, page, text, summary, mark_as_minor, section=None):
        section = int(section) if section else None
        try:
            # verify connection
            self.get_connect()
        except Exception as e:
            error_message('{} exception: {}'.format(type(e).__name__, e))
            return False

        try:
            page.save(text, summary=summary.strip(), minor=mark_as_minor, section=section)
            return True
        except mwclient.errors.MaximumRetriesExceeded:
            error_message('MaximumRetriesExceeded..')
            # force reconnecting
            self.get_connect(force=True)
            page = self.get_page(page.name)
            self.save_page(page, text, summary, mark_as_minor, section)
        except Exception as e:
            error_message('{} exception: {}'.format(type(e).__name__, e))
        return False

    def page_attr(self, page, attr_name):
        try:

            if attr_name == 'namespace_name':
                return getattr(page, 'name').split(':')[0]

            return getattr(page, attr_name)

        except AttributeError as e:
            error_message('{} exception: {}'.format(type(e).__name__, e))

    def page_can_read(self, page):
        return page.can('read')

    def page_can_edit(self, page):
        return page.can('edit')

    def page_get_text(self, page, section=None):
        section = int(section) if section else None
        try:
            if self.page_can_read(page):
                return page.text(section=section)
        except Exception:
            pass
        return ''

    def page_sections(self, page):
        con = self.get_connect()
        data = con.parse(page=self.page_attr(page, 'page_title'), prop='sections')
        if data:
            return data.get('sections', [])
        return []

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
            m['date'] = msg.get('timestamp', {}).get('date', None)
            m['agent'] = msg.get('agent', {}).get('name', None)
            m['read'] = True if msg.get('read', False) else False
            try:
                m['timestamp'] = int(msg.get('timestamp', {}).get('utcunix'))
            except Exception:
                m['timestamp'] = 0
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

    def process_upload(self, file_handler=None, filename=None, description='', url=None):
        try:
            res = self.get_connect().upload(file=file_handler, filename=filename, description=description, url=url)
            if res['result'] == self.UPLOAD_SUCCESS:
                return True
            else:
                error_message('Error while trying to upload file {}: {}'.format(filename, res))
                return False
        except Exception as e:
            error_message('Exception while trying to upload file {}: {}'.format(filename, e))
        return False

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
        site_config = props.get_site(name)
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

        assert 'host' in site_config, 'Host is not defined for site "{}"'.format(name)

        site = self.sites.get(name, {})
        site_config_old = site.get('config', {})

        if self.is_site_changed(site_config_old, site_config):
            if not site_config_old:
                status_message("'''Setup new connection to \"{}\".'''".format(name))
            else:
                status_message("'''Site configuration is changed, setup new connection to \"{}\".. '''".format(name))
            if 'connection' in site:
                site['connection'] = None

            # TODO: rework with props
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
        #   host_key = '{}://{}'.format('https' if self.is_https else 'http', self.site)
        #   using proto only..

        return {
            'verify': site['is_ssl_cert_verify'],
            'proxies': site['proxies'],
            'timeout': (site['retry_timeout'], None)
        }

    def debug_flush(self):
        if props.get_setting('debug'):
            for msg in self.debug_msgs:
                error_message("'''DEBUG''' {}".format(msg))
        self.debug_msgs = []

    def get_connect(self, name=None, force=False):
        ''' setup new connection (call connect()) or returns exists '''

        def _get_new_connection():
            try:

                connection = self.connect(name=name)
                self.debug_flush()
                return connection

            except Exception as e:
                self.debug_msgs.append('Connection exception: {}'.format(e))

            self.debug_flush()

        if props.get_setting('offline_mode'):
            return

        self.debug_msgs.append('Get connection from connection manager.')
        # try:
        site = self.get_site(name)

        cj = None
        cookies_changed = False
        if site['authorization_type'] == self.AUTH_TYPE_COOKIES:

            cj = self.get_cookies(name=name)

            if not self.is_eq_cookies(site['cookies'], cj):
                self.debug_msgs.append('New cookies: {}'.format(cj))
                site['cookies'] = cj
                cookies_changed = True

        if cookies_changed:
            return _get_new_connection()

        if force:
            return _get_new_connection()

        if site['authorization_type'] == self.AUTH_TYPE_LOGIN and site['username'] and not site['password']:
            return _get_new_connection()

        # try to get cached connection

        connection = site.get('connection', None)

        if connection:
            self.debug_msgs.append('Cached connection: True')
            self.debug_flush()
            return connection

        return _get_new_connection()

    def connect(self, name=None):
        ''' new connection '''

        site = self.get_site(name)

        status_message('Connecting to "{}" .. '.format(self.url(name)), new_line=False)

        if site['authorization_type'] == self.AUTH_TYPE_OAUTH:
            # oauth authorization
            connection = self._oauth()
        else:
            # Site connection
            try:
                connection = mwclient.Site(
                    host=site['hosturl'],
                    path=site['path'],
                    # retry_timeout=None,
                    # max_retries=None,
                    retry_timeout=10,
                    max_retries=3,
                    requests=self.get_requests_config(name)
                )
            except requests.exceptions.HTTPError as e:
                if props.get_setting('debug'):
                    self.debug_msgs.append('HTTP response: {}'.format(e))

                # additional http auth (basic, digest)
                if e.response.status_code == 401 and site['use_http_auth']:
                    http_auth_header = e.response.headers.get('www-authenticate', '')
                    self.debug_msgs.append('www-authenticate header: {}'.format(http_auth_header))
                    connection = self._http_auth(http_auth_header=http_auth_header, name=name)
                else:
                    # sublime.message_dialog('HTTP connection failed: {}'.format(e[1]))
                    error_message(' failed: {}'.format(e[1]))
                    return
            except Exception as e:
                # sublime.message_dialog('Connection failed for {}: {}'.format(site['hosturl'], e))
                error_message(' failed: {}'.format(e))
                return

        if connection:
            status_message(' done.')
            if props.get_setting('debug'):
                self.debug_msgs.append('Connection: {}'.format(connection.connection))

            status_message(
                'Login in with authorization type {}{}.. '.format(
                    site['authorization_type'],
                    ' ({})'.format(site['cookies_browser']) if site['authorization_type'] == 'cookies' else ''
                ),
                new_line=False
            )
            success_message = ' done'
            # Cookie auth
            if site['authorization_type'] == self.AUTH_TYPE_COOKIES and site['cookies']:
                try:
                    connection.login(cookies=site['cookies'])

                    if props.get_setting('debug'):
                        self.debug_msgs.append('OS: {}, arch: {}'.format(
                            sublime.platform(),
                            sublime.arch()
                        ))
                        self.debug_msgs.append('Username: {}'.format(connection.username.strip()))
                        # not connection.logged_in and self.debug_msgs.append('* Anonymous connection: True')
                        self.debug_msgs.append('Anonymous connection: True') if not connection.logged_in else None
                        self.debug_msgs.append('Connection rights: {}'.format(', '.join(connection.rights)))
                        self.debug_msgs.append('Connection tokens: {}'.format(', '.join(['{}: {}'.format(
                            t,
                            connection.tokens[t]
                        ) for t in connection.tokens.keys()]) if connection.tokens else '<empty>'))

                except mwclient.LoginError as exc:
                    e = exc.args
                    error_message(' failed: {}'.format(e[1]['result']))
                    return
            # Login/Password auth
            elif site['authorization_type'] == self.AUTH_TYPE_LOGIN and site['username'] and site['password']:
                try:
                    # TODO: replace with `clientlogin` or leave for just "bot" connects
                    connection.login(username=site['username'], password=site['password'], domain=site['domain'])
                except mwclient.LoginError as exc:
                    e = exc.args
                    error_message(' failed: {}, exception: {}'.format(
                        e[1].get('result'),
                        e
                    ))

                    status_message('Old type auth (`login`) failed, trying `clientlogin`..', new_line=False)
                    try:
                        connection.clientlogin(username=site['username'], password=site['password'])
                    except mwclient.LoginError as exc:
                        e = exc.args
                        error_message(' failed: {}, exception: {}'.format(
                            e[1].get('message'),
                            e
                        ))
                        return
            else:
                success_message = ' done, without authorization.'  # TODO: recheck AUTH messages

            status_message(success_message)

            site['connection'] = connection
            return connection
        else:
            error_message(' failed.')

        return

    def require_password(self, name=None):

        site = self.get_site(name)
        if site['authorization_type'] == self.AUTH_TYPE_LOGIN and site.get('username') and not site.get('password'):
            return True
        return False

    def url(self, name=None):
        site = self.get_site(name)
        return ''.join([site['hosturl'][0], '://', site['hosturl'][1]])

    def get_cookies(self, name):
        site = self.get_site(name)

        if site['authorization_type'] != self.AUTH_TYPE_COOKIES:
            return None

        cookie_files = props.get_setting('{}_cookie_files'.format(site['cookies_browser']), [])
        if not cookie_files:
            cookie_files = None

        if site['cookies_browser'] == "firefox":
            return browser_cookie3.firefox(
                cookie_file=cookie_files[0] if cookie_files else None,
                domain_name=site['host'],
                copy_path=p.from_package(name='User', posix=True, is_abs=True)
            )
        elif site['cookies_browser'] == 'chrome':
            return browser_cookie3.chrome(
                cookie_file=cookie_files[0] if cookie_files else None,
                domain_name=site['host']
            )
        else:
            sublime.message_dialog("Incompatible browser for cookie: {}".format(site['cookies_browser'] or "Not defined"))

        return None

    def is_eq_cookies(self, cj1, cj2):
        cj1_set = set((c.domain, c.path, c.name, c.value) for c in cj1) if cj1 else set()
        cj2_set = set((c.domain, c.path, c.name, c.value) for c in cj2) if cj2 else set()
        return not bool(cj1_set - cj2_set or cj2_set - cj1_set)

    def _http_auth(self, http_auth_header, name=None):
        DIGEST_REALM = 'Digest realm'
        BASIC_REALM = 'Basic realm'

        if not http_auth_header:
            error_message('Unable to get authorization type: header is empty')
            return

        site = self.get_site(name)

        http_auth_login = site['http_auth_login']
        http_auth_password = site['http_auth_password']

        if not http_auth_login or not http_auth_password:
            return None

        header_tokens = [v.strip() for v in http_auth_header.split(',')]

        realm = None

        for token in header_tokens:
            if token.startswith(DIGEST_REALM):
                # digest in higher priority
                realm = DIGEST_REALM
                break
            elif token.startswith(BASIC_REALM):
                realm = BASIC_REALM

        if not realm:
            error_message('Unable to find supported realm for http authorization, header: {}'.format(http_auth_header))
            return

        httpauth = None

        if realm == BASIC_REALM:
            httpauth = requests.auth.HTTPBasicAuth(http_auth_login, http_auth_password)
        elif realm == DIGEST_REALM:
            httpauth = requests.auth.HTTPDigestAuth(http_auth_login, http_auth_password)

        if httpauth:
            connection = mwclient.Site(
                host=site['hosturl'],
                path=site['path'],
                retry_timeout=10,
                max_retries=3,
                httpauth=httpauth,
                requests=self.get_requests_config(name))
            return connection

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
                    host=site['hosturl'],
                    path=site['path'],
                    # retry_timeout=None,
                    # max_retries=None,
                    retry_timeout=10,
                    max_retries=3,
                    consumer_token=site['oauth_consumer_token'],
                    consumer_secret=site['oauth_consumer_secret'],
                    access_token=site['oauth_access_token'],
                    access_secret=site['oauth_access_secret'],
                    requests=self.get_requests_config(name)
                )
                return connection
            except mwclient.OAuthAuthorizationError as exc:
                e = exc.args
                error_message('OAuth login failed: {}'.format(e[1]))
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

    def get_title(self, title=None):
        if not title:
            title_pre = ''
            # use clipboard or selected text for page name
            if bool(props.get_setting('clipboard_as_defaultpagename')):
                title_pre = sublime.get_clipboard().strip()
            if not title_pre:
                selection = self.window.active_view().sel()
                title_pre = self.window.active_view().substr(selection[0]).strip()
            self.show_input('Wiki page name ({}):'.format(get_view_site()), title_pre)
        else:
            self.on_done(title)

    def on_change(self, title):
        if title:
            pagename_cleared = pagename_clear(title)
            if title != pagename_cleared:
                self.window.show_input_panel('Wiki page name ({}):'.format(get_view_site()),
                                             pagename_cleared, self.on_done, self.on_change, None)

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
                self.is_hide_password = props.get_setting('password_input_hide')
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
        password_char = props.get_setting('password_char', '*')
        if len(password) < len(self.password):
            self.password = self.password[:len(password)]
        else:
            try:
                self.password = '{}{}'.format(self.password, password.replace(password_char, ''))
            except Exception:
                pass
        return password_char * len(self.password)

    def done(self):
        try:
            return self.password
        except Exception:
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
            for pk in self.params.keys():
                param = '{}={}'.format(pk, self.params[pk])
                params_list.append(param)
        return params_list
