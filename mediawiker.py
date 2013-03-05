#!/usr/bin/env python\n
# -*- coding: utf-8 -*-

import mwclient
import webbrowser
import urllib
from os.path import splitext, basename
import sublime
import sublime_plugin
#http://www.sublimetext.com/docs/2/api_reference.html
#sublime.message_dialog


def mediawiker_get_setting(key, default_value=None):
    settings = sublime.load_settings('Mediawiker.sublime-settings')
    return settings.get(key, default_value)


def mediawiker_set_setting(key, value):
    settings = sublime.load_settings('Mediawiker.sublime-settings')
    settings.set(key, value)
    sublime.save_settings("Mediawiker.sublime-settings")


def mediawiker_get_connect(password=''):
    site_name_active = mediawiker_get_setting('mediawiki_site_active')
    site_list = mediawiker_get_setting('mediawiki_site')
    site = site_list[site_name_active]["host"]
    path = site_list[site_name_active]["path"]
    username = site_list[site_name_active]["username"]
    domain = site_list[site_name_active]["domain"]
    sitecon = mwclient.Site(site, path)
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


def mediawiker_pagename_clear(pagename):
    """ Return clear pagename if page-url was set instead of.."""
    site_name_active = mediawiker_get_setting('mediawiki_site_active')
    site_list = mediawiker_get_setting('mediawiki_site')
    site = site_list[site_name_active]["host"]
    pagepath = site_list[site_name_active]["pagepath"]
    if site in pagename:
        pageindex = pagename.find(site) + len(site) + len(pagepath)
        pagename = pagename[pageindex:]
        try:
            pagename = urllib.unquote(pagename.encode('ascii')).decode('utf-8')
        except UnicodeEncodeError:
            return pagename
        except Exception:
            return pagename
    return pagename


def mediawiker_save_mypages(title):
    #for wiki '_' and ' ' are equal in page name
    title = title.replace('_', ' ')
    pagelist_maxsize = mediawiker_get_setting('mediawiker_pagelist_maxsize')
    site_name_active = mediawiker_get_setting('mediawiki_site_active')
    mediawiker_pagelist = mediawiker_get_setting('mediawiker_pagelist', {})

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
    mediawiker_set_setting('mediawiker_pagelist', mediawiker_pagelist)


def mediawiker_get_title(view_name, file_name):
    ''' returns page title from view_name or from file_name'''

    if view_name:
        return view_name
    elif file_name:
        wiki_extensions = mediawiker_get_setting('mediawiker_files_extension')
        #haven't view.name, try to get from view.file_name (without extension)
        title, ext = splitext(basename(file_name))
        if ext[1:] in wiki_extensions and title:
            return title
        else:
            sublime.status_message('Anauthorized file extension for mediawiki publishing. Check your configuration for correct extensions.')
            return ''
    else:
        return ''


class MediawikerPageCommand(sublime_plugin.WindowCommand):
    goto = ''
    inputpanel = None
    is_inputfixed = False

    def run(self, goto):
        self.goto = goto
        pagename_default = ''
        #use clipboard or selected text for page name
        if bool(mediawiker_get_setting('mediawiker_clipboard_as_defaultpagename')):
            pagename_default = sublime.get_clipboard().strip()
        if not pagename_default:
            selection = self.window.active_view().sel()
            for selreg in selection:
                pagename_default = self.window.active_view().substr(selreg).strip()

        if goto == 'mediawiker_show_page':
            #open wiki page in editor
            self.inputpanel = self.window.show_input_panel('Wiki page name:', mediawiker_pagename_clear(pagename_default), self.on_done, self.on_change, self.on_escape)
        elif goto == 'mediawiker_publish_page':
            #publish current page to wiki server
            self.on_done('')
        elif goto == 'mediawiker_add_category':
            #add category to current page
            self.on_done('')

    def on_escape(self):
        self.inputpanel = None

    def on_change(self, text):
        if not self.is_inputfixed and text and bool(mediawiker_get_setting('mediawiker_clearpagename_oninput')):
            edit = self.inputpanel.begin_edit()
            self.is_inputfixed = True
            self.inputpanel.erase(edit, sublime.Region(0, self.inputpanel.size()))
            self.inputpanel.insert(edit, 0, mediawiker_pagename_clear(text))
            self.inputpanel.end_edit(edit)
            sublime.status_message('Page name was cleared.')
            self.is_inputfixed = False

    def on_done(self, text):
        try:
            text = mediawiker_pagename_clear(text)
            self.window.run_command("mediawiker_validate_connection_params", {"title": text, "goto": self.goto})
        except ValueError, e:
            sublime.message_dialog(e)


class MediawikerPageListCommand(sublime_plugin.WindowCommand):
    my_pages = []

    def run(self):
        site_name_active = mediawiker_get_setting('mediawiki_site_active')
        mediawiker_pagelist = mediawiker_get_setting('mediawiker_pagelist', {})
        self.my_pages = mediawiker_pagelist[site_name_active] if site_name_active in mediawiker_pagelist else []
        if self.my_pages:
            self.my_pages.reverse()
            self.window.show_quick_panel(self.my_pages, self.on_done)
        else:
            sublime.status_message('List of pages for wiki "%s" is empty.' % (site_name_active))

    def on_done(self, index):
        if index >= 0:
            # escape from quick panel return -1
            text = self.my_pages[index]
            try:
                self.window.run_command("mediawiker_validate_connection_params", {"title": text, "goto": "mediawiker_show_page"})
            except ValueError, e:
                sublime.message_dialog(e)


class MediawikerValidateConnectionParamsCommand(sublime_plugin.WindowCommand):
    site = None
    password = ''
    title = ''
    goto = ''

    def run(self, title, goto):
        self.goto = goto  # TODO: check for better variant
        self.title = title
        site = mediawiker_get_setting('mediawiki_site_active')
        site_list = mediawiker_get_setting('mediawiki_site')
        self.password = site_list[site]["password"]
        if site_list[site]["username"]:
            #auth required if username exists in settings
            if not self.password:
                #need to ask for password
                self.window.show_input_panel('Password:', '', self.on_done, None, None)
            else:
                self.call_page()
        else:
            #auth is not required
            self.call_page()

    def on_done(self, password):
        self.password = password
        self.call_page()

    def call_page(self):
        self.window.active_view().run_command(self.goto, {"title": self.title,
                                                          "password": self.password})


class MediawikerShowPageCommand(sublime_plugin.TextCommand):
    def run(self, edit, title, password):
        sitecon = mediawiker_get_connect(password)
        page = sitecon.Pages[title]
        if page.can('edit'):
            text = page.edit()
            if not text:
                sublime.status_message('Wiki page %s is not exists. You can create new..' % (title))
                text = '=%s=\n<Remove this with text of the new page>\n\n[[Category:]]' % (title)
            if bool(mediawiker_get_setting('mediawiker_newtab_ongetpage', False)):
                self.view = sublime.active_window().new_file()
            else:
                #clear tab
                self.view.erase(edit, sublime.Region(0, self.view.size()))
            self.view.set_syntax_file('Packages/Mediawiker/Mediawiki.tmLanguage')
            self.view.set_name(title)
            #load page data
            self.view.insert(edit, 0, text)
            sublime.status_message('Page %s was opened successfully.' % (title))
        else:
            sublime.status_message('You have not rights to edit this page')


class MediawikerPublishPageCommand(sublime_plugin.TextCommand):
    my_pages = None
    page = None
    title = ''
    current_text = ''

    def run(self, edit, title, password):
        sitecon = mediawiker_get_connect(password)
        self.title = mediawiker_get_title(self.view.name(), self.view.file_name())
        if self.title:
            self.page = sitecon.Pages[self.title]
            self.current_text = self.view.substr(sublime.Region(0, self.view.size()))
            self.view.window().show_input_panel("Changes summary:", '', self.on_done, None, None)
        else:
            sublime.status_message('Can\'t publish page with empty title')
            return

    def on_done(self, summary):
        try:
            summary = '%s%s' % (summary, mediawiker_get_setting('mediawiker_summary_postfix', ' (by SublimeText.Mediawiker)'))
            if self.page.can('edit'):
                self.page.save(self.current_text, summary=summary)
            else:
                sublime.status_message('You have not rights to edit this page')
        except mwclient.EditError, e:
            sublime.status_message('Can\'t publish page %s (%s)' % (self.title, e))
        sublime.status_message('Wiki page %s was successfully published to wiki.' % (self.title))
        #save my pages
        mediawiker_save_mypages(self.title)


class MediawikerShowTocCommand(sublime_plugin.TextCommand):
    items = []
    regions = []

    def run(self, edit):
        self.items = []
        self.regions = []
        pattern = '^={1,5}(.*)?={1,5}'
        self.regions = self.view.find_all(pattern)
        for r in self.regions:
            item = self.view.substr(r).strip(' \t').rstrip('=').replace('=', '  ')
            self.items.append(item)
        self.view.window().show_quick_panel(self.items, self.on_done)

    def on_done(self, index):
        if index >= 0:
            # escape from quick panel return -1
            self.view.show(self.regions[index])
            self.view.sel().clear()
            self.view.sel().add(self.regions[index])


class MediawikerSetActiveSiteCommand(sublime_plugin.TextCommand):
    site_keys = []

    def run(self, edit):
        site_active = mediawiker_get_setting('mediawiki_site_active')
        sites = mediawiker_get_setting('mediawiki_site')
        self.site_keys = sites.keys()
        for key in self.site_keys:
            if key == site_active:
                #self.site_keys[self.site_keys.index(key)] = "%s (active)" % (key)
                self.site_keys[self.site_keys.index(key)] = [key, '(active)']
        self.view.window().show_quick_panel(self.site_keys, self.on_done)

    def on_done(self, index):
        if index >= 0 and type(self.site_keys[index]) != list:
            # not escaped and not active
            mediawiker_set_setting("mediawiki_site_active", self.site_keys[index])


class MediawikerOpenPageInBrowserCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        site_name_active = mediawiker_get_setting('mediawiki_site_active')
        site_list = mediawiker_get_setting('mediawiki_site')
        site = site_list[site_name_active]["host"]
        pagepath = site_list[site_name_active]["pagepath"]
        title = mediawiker_get_title(self.view.name(), self.view.file_name())
        if title:
            webbrowser.open('http://%s%s%s' % (site, pagepath, title))
        else:
            sublime.status_message('Can\'t open page with empty title')
            return


class MediawikerAddCategoryCommand(sublime_plugin.TextCommand):
    categories_list = None
    password = ''
    title = ''

    def run(self, edit, title, password):
        sitecon = mediawiker_get_connect(self.password)
        category_root = mediawiker_get_setting('mediawiker_category_root')
        category = sitecon.Pages[category_root]
        self.categories_list_names = []
        self.categories_list_values = []
        for page in category:
            #is category namespace always has value 14?
            if page.namespace == 14:
                self.categories_list_values.append(page.name)
                self.categories_list_names.append(page.name[page.name.find(':') + 1:])
        sublime.active_window().show_quick_panel(self.categories_list_names, self.on_done)

    def on_done(self, idx):
        # the dialog was cancelled
        if idx is -1:
            return
        index_of_textend = self.view.size()
        edit = self.view.begin_edit()
        self.view.insert(edit, index_of_textend, '[[%s]]' % self.categories_list_values[idx])
        self.view.end_edit(edit)
