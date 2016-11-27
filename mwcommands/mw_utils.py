#!/usr/bin/env python\n
# -*- coding: utf-8 -*-

import sys

from os.path import splitext, basename
import re
import urllib
import webbrowser

try:
    # Python 2.7+
    from collections import OrderedDict
except ImportError:
    # Python 2.6
    from ordereddict import OrderedDict

import sublime
import sublime_plugin
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
    from html.parser import HTMLParser
    from ..lib import mwclient
    from ..lib import browser_cookie3
else:
    from HTMLParser import HTMLParser
    from lib import mwclient


CATEGORY_NAMESPACE = 14  # category namespace number
IMAGE_NAMESPACE = 6  # image namespace number
TEMPLATE_NAMESPACE = 10  # template namespace number
SCRIBUNTO_NAMESPACE = 828  # scribunto module namespace number

COMMENT_REGIONS_KEY = 'comment'


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


def set_syntax(page=None):
    syntax = get_setting('mediawiki_syntax', 'Packages/Mediawiker/MediawikiNG.tmLanguage')

    if page:
        syntax_ext = 'sublime-syntax' if int(sublime.version()) >= 3084 else 'tmLanguage'

        # Scribunto lua modules, except doc subpage
        if page.namespace == SCRIBUNTO_NAMESPACE and not page.name.lower().endswith('/doc'):
            syntax = 'Packages/Lua/Lua.%s' % syntax_ext
        elif page.name.lower().endswith('.css'):
            syntax = 'Packages/CSS/CSS.%s' % syntax_ext
        elif page.name.lower().endswith('.js'):
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


# TODO: move functions like this to connection class?
def get_connect():
    sitecon = mwcon.get_site()
    if not sitecon:
        raise Exception("No valid connection available")
    return sitecon


# wiki related functions..

def get_page(site, title):
    return site.Pages[title]


def get_page_text(page):
    if page:
        denied_message = 'You have not rights to edit this page. Click OK button to view its source.'

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
    return False, ''


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


# ###### Hover functions #######
HOVER_IMG_SIZE = 300

HOVER_HTML_HEADER = '''
<html>
    <style>
        ul { margin-left: 0; padding-left: 0rem; }
        li { margin-left: 0; display: block; }
        a {text-decoration: none; }
    </style>

    <body id="mediawiker_html">
'''

HOVER_HTML_FOOTER = '''
    </body>
</html>
'''


def on_hover_selected(view, point):

    def on_navigate_selected(link):
        if link == 'bold':
            sublime.active_window().run_command("insert_snippet", {"contents": "'''${0:$SELECTION}'''"})
        elif link == 'italic':
            sublime.active_window().run_command("insert_snippet", {"contents": "''${0:$SELECTION}''"})
        elif link == 'code':
            sublime.active_window().run_command("insert_snippet", {"contents": "<code>${0:$SELECTION}</code>"})
        elif link == 'pre':
            sublime.active_window().run_command("insert_snippet", {"contents": "<pre>${0:$SELECTION}</pre>"})
        elif link == 'nowiki':
            sublime.active_window().run_command("insert_snippet", {"contents": "<nowiki>${0:$SELECTION}</nowiki>"})
        elif link == 'kbd':
            sublime.active_window().run_command("insert_snippet", {"contents": "<kbd>${0:$SELECTION}</kbd>"})
        elif link == 'strike':
            sublime.active_window().run_command("insert_snippet", {"contents": "<s>${0:$SELECTION}</s>"})
        elif link.startswith('comment'):
            a, b = link.split(':')[-2:]
            sublime.active_window().run_command("mediawiker_edit_comment", {"a": int(a), "b": int(b)})

    selected = view.sel()
    for r in selected:
        if r and r.contains(point):
            content = [
                HOVER_HTML_HEADER,
                'Format:',
                '<ul>',
                '<li><a href="bold">Bold</a></li>',
                '<li><a href="italic">Italic</a></li>',
                '<li><a href="code">Code</a></li>',
                '<li><a href="pre">Predefined</a></li>',
                '<li><a href="nowiki">Nowiki</a></li>',
                '<li><a href="kbd">Keyboard</a></li>',
                '<li><a href="strike">Strike</a></li>',
                '<li><a href="comment:%s:%s">Comment</a></li>' % (r.a, r.b),
                '</ul>',
                HOVER_HTML_FOOTER
            ]
            content_html = ''.join(content)
            view.show_popup(
                content=content_html,
                location=point,
                flags=sublime.HIDE_ON_MOUSE_MOVE_AWAY,
                on_navigate=on_navigate_selected
            )
            return True

    return False


def on_hover_internal_link(view, point):

    def on_navigate(link):
        page_name = link.split(':', 1)[-1].replace(' ', '_')
        if link.startswith('open'):
            view.window().run_command("mediawiker_page", {
                'action': 'mediawiker_show_page',
                'action_params': {'title': page_name}
            })
        elif link.startswith('browse'):
            url = get_page_url(page_name)
            webbrowser.open(url)

    links = get_internal_links_regions(view)
    for r in links:
        if r[1].contains(point):

            is_file = False
            img_base64 = None
            if get_setting('mediawiker_show_image_in_popup', True):
                try:
                    sitecon = get_connect()
                    page = get_page(sitecon, r[0])
                    if page.namespace == IMAGE_NAMESPACE:
                        is_file = True
                        extra_properties = {
                            'imageinfo': (
                                ('iiprop', 'timestamp|user|comment|url|size|sha1|metadata|archivename'),
                                ('iiurlwidth', HOVER_IMG_SIZE)
                            )
                        }
                        img = mwclient.Image(site=sitecon, name=r[0], extra_properties=extra_properties)
                        img_remote_url = img.imageinfo['thumburl']
                        response = requests.get(img_remote_url)
                        # "http:" is not works: https://github.com/SublimeTextIssues/Core/issues/1378
                        img_base64 = "data:" + response.headers['Content-Type'] + ";" + "base64," + str(base64.b64encode(response.content).decode("utf-8"))
                except:
                    pass

            h = 'Page "%s"' % r[0] if not is_file else 'File "%s"' % r[0].split(':')[1]

            content = [
                HOVER_HTML_HEADER,
                '<h4>%s</h4>' % h,
                '<img src="%(uri)s">' % {'uri': img_base64} if img_base64 else '',
                '<ul><li><a href="open:%(point)s">Open</a> | <a href="browse:%(point)s">View in browser</a></li></ul>' % {'point': r[0]},
                HOVER_HTML_FOOTER
            ]
            content_html = ''.join(content)

            view.show_popup(
                content=content_html,
                location=point,
                max_width=500,
                max_height=500,
                flags=sublime.HIDE_ON_MOUSE_MOVE_AWAY,
                on_navigate=on_navigate
            )
            # TODO: phantoms for images
            # https://forum.sublimetext.com/t/dev-build-3118/21270
            # view.add_phantom("test", view.sel()[0], "Hello, World!", sublime.LAYOUT_BLOCK)
            # view.erase_phantoms("test")
            # img_html = '<img src="%(uri)s">' % {'uri': img_base64} if img_base64 else ''
            # view.add_phantom("image", sublime.Region(point, point), img_html, sublime.LAYOUT_BLOCK)
            return True

    return False


def get_templates(view):

    TPL_START = r'(?<![^\{]\{)\{{2}(?!\{[^\{])'
    TPL_STOP = r'(?<![^\}]\})\}{2}(?!\}([^\}]|$))'
    TYPE_START = 'start'
    TYPE_STOP = 'stop'
    text_region = sublime.Region(0, view.size())
    line_regions = view.split_by_newlines(text_region)
    # print(line_regions)
    lines_data = []
    templates = []
    for region in line_regions:
        line_text = view.substr(region)
        starts = [region.a + m.start() for m in re.finditer(TPL_START, line_text)]
        stops = [region.a + m.start() for m in re.finditer(TPL_STOP, line_text)]

        line_index = {}
        for i in starts:
            line_index[i] = TYPE_START
        for i in stops:
            line_index[i] = TYPE_STOP

        if starts or stops:
            lines_data.append(line_index)

    _templates = []
    for d in lines_data:
        line_indexes = list(d.keys())
        line_indexes.sort()
        for i in line_indexes:
            if d[i] == TYPE_START:
                t = sublime.Region(i + 2, i + 2)  # unknown end
                _templates.append(t)
            elif d[i] == TYPE_STOP:
                # ST2 compat Region update
                # _templates[-1].b = i
                if _templates:  # if smth. wrong with parsing early, list can be empty, skipping
                    _templates[-1] = sublime.Region(_templates[-1].a, i)
                    templates.append((_templates[-1], len(_templates)))  # template region and includes level
                    _templates = _templates[:-1]
    return templates


def on_hover_template(view, point):

    def on_navigate(link):
        if link.startswith('fold'):
            point = int(link.split(':')[-1])
            sublime.active_window().run_command("mediawiker_colapse", {"type": "fold", "point": point})
        elif link.startswith('unfold'):
            point = int(link.split(':')[-1])
            sublime.active_window().run_command("mediawiker_colapse", {"type": "unfold", "point": point})
        else:
            sublime.active_window().run_command("mediawiker_page", {
                'action': 'mediawiker_show_page',
                'action_params': {'title': link.replace(' ', '_')}
            })

    SCRIBUNTO_PREFIX = '#invoke'
    tpl_regions = []
    _rs = get_templates(view)
    for r in _rs:
        tpl_regions.append(r[0])

    for r in tpl_regions:
        if r.contains(point):

            template_name = view.substr(r).split('|')[0].strip()
            if template_name.startswith(SCRIBUNTO_PREFIX):
                # #invoke:ScribuntoTest
                template_name = template_name.split(':')[-1]
                template_link = 'Module:%s' % template_name
                template_type = 'Scribunto module'
            else:
                template_link = 'Template:%s' % template_name
                template_type = 'Template'

            content = [
                HOVER_HTML_HEADER,
                '<h4>%s "%s"</h4>' % (template_type, template_name),
                '<a href="%(link)s">Open</a> | <a href="fold:%(point)s">Fold</a> | <a href="unfold:%(point)s">Unfold</a>' % {'link': template_link, 'point': point},
                HOVER_HTML_FOOTER
            ]
            content_html = ''.join(content)

            view.show_popup(
                content=content_html,
                location=point,
                flags=sublime.HIDE_ON_MOUSE_MOVE_AWAY,
                on_navigate=on_navigate
            )
            return True
    return False


def on_hover_heading(view, point):

    def on_navigate(link):
        if link.startswith('fold'):
            point = int(link.split(':')[-1])
            sublime.active_window().run_command("mediawiker_colapse", {"type": "fold", "point": point})
        elif link.startswith('unfold'):
            point = int(link.split(':')[-1])
            sublime.active_window().run_command("mediawiker_colapse", {"type": "unfold", "point": point})

    h_regions = []
    for lvl in range(2, 6):
        _rs = view.get_regions('h_%s' % lvl)
        if _rs:
            h_regions = h_regions + _rs

    for r in h_regions:
        _r = sublime.Region(view.line(r).a, r.a)
        if _r.contains(point):

            h_name = view.substr(_r).replace('=', '').strip()
            content = [
                HOVER_HTML_HEADER,
                '<h4>Heading "%s"</h4>' % (h_name),
                '<a href="fold:%(point)s">Fold</a> | <a href="unfold:%(point)s">Unfold</a>' % {'point': point},
                HOVER_HTML_FOOTER
            ]
            content_html = ''.join(content)

            view.show_popup(
                content=content_html,
                location=point,
                flags=sublime.HIDE_ON_MOUSE_MOVE_AWAY,
                on_navigate=on_navigate
            )
            return True
    return False


def on_hover_tag(view, point):

    def on_navigate(link):
        if link.startswith('fold'):
            point = int(link.split(':')[-1])
            sublime.active_window().run_command("mediawiker_colapse", {"type": "fold", "point": point})
        elif link.startswith('unfold'):
            point = int(link.split(':')[-1])
            sublime.active_window().run_command("mediawiker_colapse", {"type": "unfold", "point": point})

    fold_tags = get_setting("mediawiker_fold_tags", ["source", "syntaxhighlight", "div", "pre"])
    tag_regions = []

    for tag in fold_tags:
        regs = view.get_regions(tag)
        for r in regs:
            tag_regions.append((tag, r))

    for r in tag_regions:
        if r[1].contains(point):

            content = [
                HOVER_HTML_HEADER,
                '<h4>%s</h4>' % r[0].title(),
                '<a href="fold:%(point)s">Fold</a> | <a href="unfold:%(point)s">Unfold</a>' % {'point': point},
                HOVER_HTML_FOOTER
            ]
            content_html = ''.join(content)

            view.show_popup(
                content=content_html,
                location=point,
                flags=sublime.HIDE_ON_MOUSE_MOVE_AWAY,
                on_navigate=on_navigate
            )
            return True
    return False


def on_hover_comment(view, point):

    def on_navigate(link):
        if link.startswith('fold'):
            point = int(link.split(':')[-1])
            sublime.active_window().run_command("mediawiker_colapse", {"type": "fold", "point": point})
        elif link.startswith('unfold'):
            point = int(link.split(':')[-1])
            sublime.active_window().run_command("mediawiker_colapse", {"type": "unfold", "point": point})

    def get_text_pretty(r):
        text = view.substr(r).strip().lstrip('<!--').rstrip('-->')
        text = text.replace('TODO', '<strong style="color:#E08283;">TODO</strong>')
        text = text.replace('NOTE', '<strong style="color:#26A65B;">NOTE</strong>')
        text = text.replace('WARNING', '<strong style="color:#C0392B;">WARNING</strong>')
        text = text.replace('\n', '<br>')
        return text

    comment_regions = view.get_regions('comment')

    if not comment_regions:
        return False

    for r in comment_regions:
        if r.contains(point):

            comment_text = get_text_pretty(r)
            content = [
                HOVER_HTML_HEADER,
                '<h4>Note</h4>',
                '<ul>'
                '<li>%s</li>' % comment_text,
                '<li><a href="fold:%(point)s">Fold</a> | <a href="unfold:%(point)s">Unfold</a></li>' % {'point': point},
                '</ul>',
                HOVER_HTML_FOOTER
            ]
            content_html = ''.join(content)

            view.show_popup(
                content=content_html,
                location=point,
                flags=sublime.HIDE_ON_MOUSE_MOVE_AWAY,
                on_navigate=on_navigate
            )
            return True
    return False


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

    def get_site(self):

        self._site_preinit()

        cj = self.try_cookie() if self.auth_type == self.AUTH_TYPE_COOKIES else None

        if self.auth_type == self.AUTH_TYPE_COOKIES and not self.is_eq_cookies(self.cj, cj):
            self.cj = cj
        elif self.auth_type != self.AUTH_TYPE_LOGIN or not self.username or self.password:
            sitecon = self.conns.get(self.site, None)
            if sitecon:
                return sitecon

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
                    # raise Exception('HTTP connection failed.')
                    return
            except Exception as e:
                sublime.message_dialog('Connection failed for %s: %s' % (self.host, e))
                # raise Exception('HTTP connection failed: %s' % e)
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
