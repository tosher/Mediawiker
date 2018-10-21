#!/usr/bin/env python\n
# -*- coding: utf-8 -*-

import sys

import sublime
# import sublime_plugin
import webbrowser

pythonver = sys.version_info[0]
if pythonver >= 3:
    from . import mw_utils as utils
    from . import mw_html
    from . import mw_parser as par
    from html import escape
else:
    import mw_utils as utils
    import mw_html
    from cgi import escape


html = mw_html.MwHtmlAdv(html_id='mediawiker_hover', user_css=False)
html.css_rules['ul'] = {'margin-left': '0', 'padding-left': '0rem'}
html.css_rules['li'] = {'margin-left': '0', 'display': 'block'}
html.css_rules['a']['text-decoration'] = 'none'
html.css_rules['body']['padding'] = '1rem 2rem 1rem 2rem'
html.css_rules['.undefined'] = {'padding': '5px', 'color': '#c0c0c0'}
html.css_rules['.note'] = {'padding': '5px', 'color': '#7D9DF8'}
html.css_rules['.wide'] = {'padding-left': '0.5rem', 'padding-right': '0.5rem'}
html.css_rules['.redlink'] = {'padding': '0px', 'color': '#c0392b'}


def get_popup_flags(view):
    if utils.props.get_view_setting(view, 'popups_off'):
        return None
    popup_type = utils.props.get_setting('popup_type')
    if popup_type == 'manual':
        return 0
    elif popup_type == 'auto':
        return sublime.HIDE_ON_MOUSE_MOVE_AWAY
    elif popup_type == 'off':
        return None
    return sublime.HIDE_ON_MOUSE_MOVE_AWAY


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
            sublime.active_window().run_command("insert_snippet", {"contents": "<!-- ${0:$SELECTION} -->"})

    popup_flags = get_popup_flags(view)
    if popup_flags is None:
        return

    selected = view.sel()
    for r in selected:
        if r and r.contains(point):

            content = [
                html.unnumbered_list(
                    html.span('from %s to %s' % (r.a, r.b)),
                    html.link('bold', 'Bold'),
                    html.link('italic', 'Italic'),
                    html.link('code', 'Code'),
                    html.link('pre', 'Pre'),
                    html.link('nowiki', 'Nowiki'),
                    html.link('kbd', 'Keyboard'),
                    html.link('strike', 'Strike'),
                    html.link('comment', 'Comment'),
                    css_class='undefined'
                )
            ]

            content_html = html.build(content)
            view.show_popup(
                content=content_html,
                location=point,
                flags=popup_flags,
                on_navigate=on_navigate_selected
            )
            return True

    return False


def on_hover_internal_link(view, point):

    def on_navigate(link):
        page_name = link.split(':', 1)[-1].replace(' ', '_')
        if link.startswith('open'):
            view.window().run_command(utils.cmd('page'), {
                'action': utils.cmd('show_page'),
                'action_params': {'title': page_name}
            })
        elif link.startswith('browse'):
            url = utils.get_page_url(page_name)
            webbrowser.open(url)
        elif link.startswith('get_image'):
            webbrowser.open(page_name)

    popup_flags = get_popup_flags(view)
    if popup_flags is None:
        return

    p = par.Parser(view)
    p.register_all(par.Comment, par.Link, par.Pre, par.Source, par.Nowiki)
    if not p.parse():
        return

    links = p.links

    for l in links:
        if l.region.contains(point):

            if l.name:
                page_name = l.name
                if l.name.startswith('/'):
                    # subpage
                    page_name = '%s%s' % (utils.get_title(), l.name)

                page = utils.api.get_page(page_name)
                css_class = None if page.exists else 'redlink'
                page_talk = utils.api.get_page_talk_page(page)
                css_class_talk = None if page_talk.exists else 'redlink'

                img_data = None
                if utils.props.get_setting('show_image_in_popup'):
                    try:
                        img_data, img_size, img_url = utils.api.call('get_image', title=page_name, thumb_size=utils.props.get_setting('popup_image_size'))
                    except:
                        pass

                h = 'Page "%s"' % html.span(page_name, css_class=css_class) if not img_data else 'File "%s"' % utils.api.page_attr(page, 'page_title')
                content = [
                    html.h(lvl=4, title=h),
                    html.img(uri=img_data) if img_data else '',
                    html.br(cnt=2) if img_data else '',
                    html.join(
                        html.link('open:%s' % page_name, 'Open' if page.exists else 'Create', css_class=css_class),
                        html.link('browse:%s' % page_name, 'View in browser', css_class=css_class),
                        html.link('get_image:%s' % img_url, 'View image in browser') if img_data else '',
                        char=html.span('|', css_class='wide')
                    ),
                    html.br(cnt=1),
                    html.join(
                        html.link('open:%s' % utils.api.page_attr(page_talk, 'name'), 'Open talk page' if page_talk.exists else 'Create talk page', css_class=css_class_talk),
                        html.link('browse:%s' % utils.api.page_attr(page_talk, 'name'), 'View talk page in browser', css_class=css_class_talk),
                        char=html.span('|', css_class='wide')
                    )
                ]

                content_html = html.build(content)
                view.show_popup(
                    content=content_html,
                    location=point,
                    max_width=img_size + 150 if img_data else 800,
                    max_height=img_size + 150 if img_data else 600,
                    flags=popup_flags,
                    on_navigate=on_navigate
                )
                return True

    return False


def on_hover_template(view, point):

    def on_navigate(link):
        if link == 'fold':
            for t in p.templates:
                if t.region.contains(point):
                    r.fold()
                    return
        elif link == 'unfold':
            for t in p.templates:
                if t.region.contains(point):
                    r.unfold()
                    return
        else:
            sublime.active_window().run_command(utils.cmd('page'), {
                'action': utils.cmd('show_page'),
                'action_params': {'title': link.replace(' ', '_')}
            })

    popup_flags = get_popup_flags(view)
    if popup_flags is None:
        return

    p = par.Parser(view)
    # p.debug = True
    p.register_all(par.Comment, par.TemplateAttribute, par.Template, par.Pre, par.Source, par.Nowiki)
    if not p.parse():
        return

    p.templates.reverse()
    for r in p.templates:
        if r.region.contains(point):

            page = None
            css_class = None
            page_exists = None

            template_type = 'Template'
            if r.mode == r.MODE_SCRIBUNTO:
                template_type = 'Scribunto module'
            elif r.mode == r.MODE_TRANSCLUSION:
                template_type = 'Transclusion of page'
            elif r.mode == r.MODE_FUNCTION:
                template_type = 'Function'
            elif r.mode == r.MODE_VAR:
                template_type = 'Variable'

            if r.page_name:
                page = utils.api.get_page(r.page_name)
                css_class = None if page.exists else 'redlink'
                page_exists = page.exists

            content = [
                html.h(4, '%s "%s"' % (template_type, r.page_name or r.title) if (r.page_name or r.title) else template_type),
                html.join(
                    html.link(r.page_name, 'Open' if page_exists else 'Create', css_class=css_class) if r.page_name else '',
                    html.link('fold', 'Fold'),
                    html.link('unfold', 'Unfold'),
                    char=html.span('|', css_class='wide')
                )
            ]
            content_html = html.build(content)

            view.show_popup(
                content=content_html,
                location=point,
                flags=popup_flags,
                on_navigate=on_navigate,
                max_width=800
            )
            return True
    return False


def on_hover_table(view, point):

    def on_navigate(link):
        if link == 'fold':
            for t in p.wikitables:
                if t.region.contains(point):
                    r.fold()
                    return
        elif link == 'unfold':
            for t in p.wikitables:
                if t.region.contains(point):
                    r.unfold()
                    return

    popup_flags = get_popup_flags(view)
    if popup_flags is None:
        return

    p = par.Parser(view)
    p.register_all(par.Comment, par.TemplateAttribute, par.Template, par.Pre, par.Source, par.Nowiki, par.WikiTable)
    if not p.parse():
        return

    p.wikitables.reverse()

    for r in p.wikitables:
        if r.region.contains(point):

            content = [
                html.h(4, 'Table'),
                html.join(
                    html.link('fold', 'Fold'),
                    html.link('unfold', 'Unfold'),
                    char=html.span('|', css_class='wide')
                )
            ]
            content_html = html.build(content)

            view.show_popup(
                content=content_html,
                location=point,
                flags=popup_flags,
                on_navigate=on_navigate,
                max_width=800
            )
            return True
    return False


def on_hover_heading(view, point):

    def on_navigate(link):
        if link.startswith('fold'):
            for h in headers:
                if h.region.contains(point):
                    h.fold()
                    return
        elif link.startswith('unfold'):
            for h in headers:
                if h.region.contains(point):
                    h.unfold()
                    return

    popup_flags = get_popup_flags(view)
    if popup_flags is None:
        return

    p = par.Parser(view)
    p.register_all(
        par.Comment, par.Pre,
        par.Source, par.Nowiki, par.HeaderOne,
        par.HeaderTwo, par.HeaderThree,
        par.HeaderFour, par.HeaderFive
    )
    if not p.parse():
        return

    headers = p.headerfives + p.headerfours + p.headerthrees + p.headertwos + p.headerones

    for h in headers:
        if h.region.contains(point):
            content = [
                html.h(4, 'Heading "%s"' % h.title),
                html.join(
                    html.link('fold', 'Fold'),
                    html.link('unfold', 'Unfold'),
                    char=html.span('|', css_class='wide')
                )
            ]
            content_html = html.build(content)

            view.show_popup(
                content=content_html,
                location=point,
                flags=popup_flags,
                on_navigate=on_navigate,
                max_width=800
            )
            return True
    return False


def on_hover_tag(view, point):

    def on_navigate(link):
        if link.startswith('fold'):
            for tag in tags:
                if tag.region.contains(point):
                    tag.fold()
                    return
        elif link.startswith('unfold'):
            for tag in tags:
                if tag.region.contains(point):
                    tag.unfold()
                    return

    popup_flags = get_popup_flags(view)
    if popup_flags is None:
        return

    fold_tags = utils.props.get_setting("fold_tags")

    p = par.Parser(view)
    p.register_all(
        par.Comment, par.TemplateAttribute, par.Template, par.Link, par.Pre,
        par.Source, par.Nowiki
    )

    for tag in fold_tags:
        p.register_dynamic(tag)

    if not p.parse():
        return

    tags = p.pres + p.sources
    for tag in fold_tags:
        tags_list = p.elist_by_name(tag)
        if tags_list:
            tags += tags_list

    tags.sort(key=lambda x: x.region.a, reverse=True)
    for tag in tags:
        if tag.region.contains(point):

            content = [
                html.h(4, 'Tag "%s"' % tag.title.title()),
                html.join(
                    html.link('fold', 'Fold'),
                    html.link('unfold', 'Unfold'),
                    char=html.span('|', css_class='wide')
                )
            ]
            content_html = html.build(content)

            view.show_popup(
                content=content_html,
                location=point,
                flags=popup_flags,
                on_navigate=on_navigate
            )
            return True
    return False


def on_hover_comment(view, point):

    def on_navigate(link):
        if link.startswith('fold'):
            for r in p.comments:
                if r.region.contains(point):
                    r.fold()
                    return
        elif link.startswith('unfold'):
            for r in p.comments:
                if r.region.contains(point):
                    r.unfold()
                    return

    def get_text_pretty(text):
        text = escape(text)
        text = text.replace('TODO', html.strong('TODO', css_class='success'))
        text = text.replace('NOTE', html.strong('NOTE', css_class='note'))
        text = text.replace('WARNING', html.strong('WARNING', css_class='error'))
        text = text.replace('\n', html.br())
        return text

    popup_flags = get_popup_flags(view)
    if popup_flags is None:
        return

    p = par.Parser(view)
    p.register_all(
        par.Comment, par.Pre, par.Source, par.Nowiki
    )
    if not p.parse():
        return

    for r in p.comments:
        if r.region.contains(point):

            content = [
                html.h(4, 'Commented text'),
                html.div(get_text_pretty(r.text), css_class='undefined'),
                html.br(cnt=2),
                html.join(
                    html.link('fold', 'Fold'),
                    html.link('unfold', 'Unfold'),
                    char=html.span('|', css_class='wide')
                )
            ]
            content_html = html.build(content)

            view.show_popup(
                content=content_html,
                location=point,
                flags=popup_flags,
                on_navigate=on_navigate,
                max_width=800,
                max_height=600
            )
            return True
    return False
