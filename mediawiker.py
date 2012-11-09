#!/usr/bin/env python\n
# -*- coding: utf-8 -*-

import mwclient
import webbrowser
import sublime, sublime_plugin
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
    pageindex = pagename.find(site) + len(site) + len(pagepath)
    return pagename[pageindex:]


def mediawiker_save_mypages(title):
    #for wiki '_' and ' ' are equal in page name
    title = title.replace('_', ' ')
    pagelist_maxsize = mediawiker_get_setting('mediawiker_pagelist_maxsize')
    site_name_active = mediawiker_get_setting('mediawiki_site_active')
    mediawiker_pagelist = mediawiker_get_setting('mediawiker_pagelist')
    my_pages = mediawiker_pagelist[site_name_active]

    while len(my_pages) >= pagelist_maxsize:
        my_pages.pop(0)

    if my_pages and type(my_pages) == list:
        if title in my_pages:
            #for sorting
            my_pages.remove(title)
    else:
        my_pages = []
    my_pages.append(title)
    mediawiker_set_setting('mediawiker_pagelist', mediawiker_pagelist)

class MediawikerPageCommand(sublime_plugin.WindowCommand):
    goto = ''
    def run(self, goto):
        self.goto = goto
        pagename_default = sublime.get_clipboard() if bool(mediawiker_get_setting('mediawiker_clipboard_as_defaultpagename')) else ''
        if goto == "mediawiker_show_page":
            self.window.show_input_panel("Wiki page name:", pagename_default, self.on_done, None, None)
        elif goto == "mediawiker_publish_page":
            self.on_done('')

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
        mediawiker_pagelist = mediawiker_get_setting('mediawiker_pagelist')
        self.my_pages = mediawiker_pagelist[site_name_active]
        self.my_pages.reverse()
        if self.my_pages and type(self.my_pages) == list:
            self.window.show_quick_panel(self.my_pages, self.on_done)
        else:
            return

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
                self.view.run_command('select_all')
                self.view.run_command('right_delete')
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
        self.title = self.view.name()
        self.page = sitecon.Pages[self.title]
        self.current_text = self.view.substr(sublime.Region(0, self.view.size()))
        self.view.window().show_input_panel("Changes summary:", '', self.on_done, None, None)

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
        webbrowser.open('http://%s%s%s' % (site, pagepath, self.view.name()))