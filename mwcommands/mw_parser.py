#!/usr/bin/env python\n
# -*- coding: utf-8 -*-

import sys

import sublime

# p = Parser(view)
# p.register(Comment)
# p.register(Template)
# p.register(Link)
# p.register(HtmlPre)
# p.register(Source)
# p.register(HeaderOne)
# p.register(HeaderTwo)
# p.register(HeaderThree)
# p.register(HeaderFour)
# p.register(HeaderFive)
# p.register(Bold)
# p.register(Italic)
# p.register_dynamic('div')
# p.parse()


class Element(object):

    # selfgreedy? template inside template - ok, source inside source - NOT!
    greedy = 0  # greedy level, max => greediest
    open_tag = None
    close_tag = None
    own_tags = []
    debug = False

    def __init__(self, view):
        self.points = [None, None]
        self.region = None
        self.view = view

    def validate_start(self, r, tag):
        return True

    def validate_stop(self, r, tag):
        return True

    def start(self, r_a, tag):
        self.points[0] = r_a
        self.open_tag = tag
        if self.debug:
            print('Got start of %s, open with: %s at %s' % (
                self.__class__.__name__, self.open_tag, self.points[0]))

        return True

    def stop(self, r_b, tag):
        self.close_tag = tag
        self.points[1] = r_b
        self.region = sublime.Region(self.points[0], self.points[1])
        self.data = self.get_data()
        self.region_text = self.get_region_text()
        self.text = self.get_text()
        self.set_attrs()
        if self.debug:
            print('Got new closed %s: %s, open: %s, close: %s(%s-%s)' % (
                self.__class__.__name__, self.data, self.open_tag, self.close_tag,
                self.region.a, self.region.b))

        return True

    def set_attrs(self):
        pass

    def is_closed(self):
        return True if self.region is not None else False

    def get_data(self):
        return self.view.substr(self.region).strip()

    def get_region_text(self):
        return sublime.Region(self.region.a + len(self.open_tag), self.region.b - len(self.close_tag))

    def get_text(self):
        # return self.data[len(self.open_tag):-len(self.close_tag)]
        return self.view.substr(self.region_text)

    def is_in(self, point):
        return self.region.contains(point)

    def fold(self):
        self.view.fold(self.region_text)

    def unfold(self):
        self.view.unfold(self.region)


class SimpleHtml(Element):
    START = ()
    STOP = ()

    def get_tag_open_line(self):
        return self.data.split('>')[0]

    def set_attrs(self):
        self.region_text = sublime.Region(self.region.a + len(self.get_tag_open_line()) + 1, self.region.b - len(self.close_tag))
        self.text = self.get_text()
        self.title = self.get_title()

    def get_text(self):
        return self.view.substr(self.region_text).strip()

    def get_title(self):
        return self.open_tag[1:]


class WikiTable(Element):
    START = ('{|',)
    STOP = ('|}',)


class Template(Element):
    START = ('{{', '{{:', '{{#invoke:', '{{#var:', '{{#vardefine:', '{{#expr:', '{{#vardefineecho:', '{{#varexists:', '{{#var_final:')
    STOP = ('}}',)

    MODE_TEMPLATE = 'template'
    MODE_TRANSCLUSION = 'transclusion'
    MODE_SCRIBUNTO = 'scribunto'
    MODE_VAR = 'Variable'

    modes = {
        START[0]: MODE_TEMPLATE,
        START[1]: MODE_TRANSCLUSION,
        START[2]: MODE_SCRIBUNTO,
        START[3]: MODE_VAR,
        START[4]: MODE_VAR,
        START[5]: MODE_VAR,
        START[6]: MODE_VAR,
        START[7]: MODE_VAR,
        START[8]: MODE_VAR

    }

    def mode(self):
        if self.is_closed():
            return self.modes[self.open_tag]
        return None

    def get_namespace(self):
        if self.mode == self.MODE_SCRIBUNTO:
            return 'Module'
        elif self.mode == self.MODE_TRANSCLUSION:
            return ''
        elif self.mode == self.MODE_VAR:
            return 'Variable'
        else:
            return 'Template'

    def get_name(self):
        return self.text.split('|')[0].strip()

    def get_title(self):

        if self.mode == self.MODE_SCRIBUNTO:
            return self.name.split(':')[-1]
        elif self.mode == self.MODE_TRANSCLUSION:
            return self.name[1:]
        else:
            return self.name

    def get_page_name(self):
        if self.mode == self.MODE_TRANSCLUSION:
            return self.name
        if self.mode == self.MODE_VAR:
            return None
        else:
            return '%s:%s' % (self.namespace, self.title)

    def set_attrs(self):
        self.mode = self.mode()
        self.name = self.get_name()
        self.namespace = self.get_namespace()
        self.title = self.get_title()
        self.page_name = self.get_page_name()


class ExternalLink(Element):
    START = ('[', 'http://', 'https://')
    STOP = (']',)

    MODE_MARKUP = 'markup'
    MODE_TEXT = 'text'

    def mode(self):
        if self.open_tag == self.START[0]:
            return self.MODE_MARKUP
        return self.MODE_TEXT

    def start(self, r_a, tag):
        if super(ExternalLink, self).start(r_a, tag):
            self.mode = self.mode()
            if self.open_tag.startswith('http'):
                end = self.view.find(r'\s', r_a)
                if end:
                    self.stop(end.b - 1, '')
            return True
        return False

    def set_attrs(self):
        self.url = self.get_url()
        self.anchor = self.get_anchor()
        self.alter_text = self.get_alter_text()

    def get_region_text(self):
        if self.mode == self.MODE_MARKUP:
            return sublime.Region(self.region.a + len(self.open_tag), self.region.b - len(self.close_tag))
        else:
            return self.region

    def get_text(self):
        return self.view.substr(self.region_text)

    def get_url(self):
        if self.mode == self.MODE_MARKUP:
            return self.text.split(' ')[0].split('#')[0]
        else:
            return self.text.split('#')[0]

    def get_alter_text(self):
        if self.mode == self.MODE_MARKUP:
            return self.text.split(' ')[1] if ' ' in self.text else ''
        return ''

    def get_anchor(self):
        if self.mode == self.MODE_MARKUP:
            return self.text.split(' ')[0].split('#')[1] if '#' in self.text else ''
        else:
            return self.text.split('#')[1] if '#' in self.text else ''


class Link(Element):
    START = ('[[',)
    STOP = (']]',)

    def get_name(self):
        return self.text.split('|')[0].split('#')[0]

    def get_namespace(self):
        return self.name.split(':')[0] if ':' in self.name else None

    def get_anchor(self):
        full_url = self.text.split('|')[0]
        if '#' in full_url:
            return full_url.split('#')[0]
        return None

    def get_alter_text(self):
        if '|' in self.text:
            return self.text.split('|')[1]
        return None

    def get_spaced(self, text):
        return text.replace('_', ' ')

    def get_unspaced(self, text):
        return text.replace(' ', '_')

    def get_titled(self, text):
        if len(text) > 1:
            return '%s%s' % (text[0].upper(), text[1:])
        elif len(text) == 1:
            return text.upper()
        return ''

    def set_attrs(self):
        self.name = self.get_name()
        self.namespace = self.get_namespace()
        self.title = self.name if ':' not in self.name else self.name.split(':')[1]
        self.anchor = self.get_anchor()
        self.alter_text = self.get_alter_text()


class Comment(Element):
    START = ('<!--',)
    STOP = ('-->',)
    greedy = 1

    def set_attrs(self):
        self.text = self.get_text()

    def get_text(self):
        return self.view.substr(self.region_text).strip()


class TemplateAttribute(Element):
    START = ('{{{',)
    STOP = ('}}}',)
    greedy = 1


class Pre(SimpleHtml):
    START = ('<pre',)
    STOP = ('</pre>',)
    greedy = 1
    own_tags = ['pre']


class Source(SimpleHtml):
    START = ('<source', '<syntaxhighlight')
    STOP = ('</source>', '</syntaxhighlight>')
    greedy = 1  # TODO: inside tag comment maybe greedy
    own_tags = ['source', 'syntaxhighlight']


class HeaderOne(Element):
    START = ('\n=',)
    STOP = ('=\n',)
    RESERVED_CHAR = '='
    level = 1

    def validate_start(self, r, tag):
        v = self.view
        if v.substr(r.b) == self.RESERVED_CHAR:
            return False
        return True

    def validate_stop(self, r, tag):
        v = self.view
        if v.substr(r.a - 1) == self.RESERVED_CHAR:
            return False
        return True

    def set_attrs(self):
        self.region = sublime.Region(self.region.a + 1, self.region.b - 1)
        self.data = self.get_data()
        next_region_a = self.get_next()
        self.region_text = sublime.Region(self.region.b + 1, next_region_a - 1 if next_region_a < self.view.size() else next_region_a)
        self.text = self.get_text()
        self.title = self.get_title()

    def fold(self):
        point_fold_b = self.region_text.b - len(self.open_tag) - 1 if self.region_text.b < self.view.size() else self.region_text.b
        self.view.fold(sublime.Region(self.region.b, point_fold_b))

    def unfold(self):
        self.view.unfold(sublime.Region(self.region.a, self.region_text.b))

    def get_text(self):
        v = self.view
        return v.substr(self.region_text)

    def get_title(self):
        return self.data[len(self.open_tag):-len(self.close_tag)].strip()

    def get_next(self):
        v = self.view
        next_h = v.find(r'%s[^\%s]' % (self.open_tag, self.RESERVED_CHAR), self.region.b + 1).b
        return next_h if next_h > 0 else v.size()


class HeaderTwo(HeaderOne):
    START = ('\n==',)
    STOP = ('==\n',)
    level = 2


class HeaderThree(HeaderOne):
    START = ('\n===',)
    STOP = ('===\n',)
    level = 3


class HeaderFour(HeaderOne):
    START = ('\n====',)
    STOP = ('====\n',)
    level = 4


class HeaderFive(HeaderOne):
    START = ('\n=====',)
    STOP = ('=====\n',)
    level = 5


class Bold(Element):

    START = ("'''",)
    STOP = ("'''",)
    RESERVED_CHAR = "'"


class Italic(Element):

    START = ("''",)
    STOP = ("''",)
    RESERVED_CHAR = "'"

    def validate_start(self, r, tag):
        v = self.view
        if v.substr(r.b) == self.RESERVED_CHAR:
            # if next char is ', it's a bold
            return False
        return True

    def validate_stop(self, r, tag):
        v = self.view
        if v.substr(r.b) == self.RESERVED_CHAR:
            # if next char is ', it's a bold
            return False
        return True


class Parser(object):

    denied_chars = [' ', '\n', '\r']
    debug = False
    debug_regions = []

    def __init__(self, view):
        self.view = view
        self.elements = []
        self.open_tags = ()
        self.close_tags = ()
        self.owned_tags = []

    def elist_name(self, c):
        return '%ss' % c.__name__.lower()

    def elist_by_name(self, name):
        try:
            return getattr(self, '%ss' % name)
        except AttributeError:
            return None

    def register_all(self, *args):
        for c in args:
            self.register(c)

    def register_dynamic(self, name, base=SimpleHtml, **kwargs):
        if name in self.owned_tags:
            return
        class_name = name.title()
        this = sys.modules[__name__]

        attrs = {
            'START': ('<%s' % name,),
            'STOP': ('</%s>' % name,)
        }
        for key in kwargs.keys():
            attrs[key] = kwargs[key]
        setattr(this, class_name, type(class_name, (base,), attrs))

        elementobj = getattr(this, class_name)
        self.register(elementobj)

    def register(self, elementobj):
        if hasattr(self, self.elist_name(elementobj)):
            return

        elementobj.debug = self.debug
        self.elements.append(elementobj)
        # reserve tag
        if elementobj.own_tags:
            self.owned_tags += elementobj.own_tags
        # list of elements of class elementobj
        setattr(self, self.elist_name(elementobj), [])
        self.open_tags = self.open_tags + elementobj.START
        self.close_tags = self.close_tags + elementobj.STOP
        self.tags = tuple(set(self.open_tags + self.close_tags))
        self.tags_maxlen = len(max(self.tags, key=len))

    def elist(self, c):
        ''' get list of elements of class c '''
        return getattr(self, self.elist_name(c))

    def elem_greedy_validate(self, c, r):

        def get_min_el_with_max_greedy():
            lmax = [e for e in els_greedy if e.greedy == el_max_greedy]
            lmax.sort(key=lambda x: x.points[0], reverse=True)
            return lmax[0]

        els_greedy = self.exists_greedy()
        if not els_greedy:
            return True

        el_max_greedy = max([e.greedy for e in els_greedy])
        if c.greedy > el_max_greedy:
            # element has max greedy level
            return True
        elif c.greedy == el_max_greedy:
            el_min_max_greedy = get_min_el_with_max_greedy()
            return True if c is el_min_max_greedy.__class__ or r.a < el_min_max_greedy.points[0] else False
        return False

    def exists_greedy(self):
        ''' returns all opened greedy tags '''
        els = []
        for e in self.elements:
            elist = self.elist(e)
            opened = self.get_max_opened_element(elist)
            if elist and e.greedy and opened:
                els.append(opened)
        return els

    def elem_init(self, c, r, tag):
        e = c(self.view)
        if e.validate_start(r, tag) and self.elem_greedy_validate(c, r):
            res = e.start(r.a, tag)
            if not res:
                return False
            self.elist(c).append(e)
            return True
        return False

    def get_max_opened_element(self, arr):
        opened = [c for c in arr if not c.is_closed()]
        return opened[-1] if opened else None

    def elem_close(self, c, r, tag):
        if not self.elist(c):
            return False

        e = self.get_max_opened_element(self.elist(c))
        if not e:
            return False
        if e.validate_stop(r, tag) and self.elem_greedy_validate(c, r):
            if not e.is_closed():
                res = e.stop(r.b, tag)
                if not res:
                    return False
            else:
                return False
        return True

    def markup(self, text, r):
        text = text.strip(' ')

        for e in self.elements:

            if self.elist(e):
                t = self.get_max_opened_element(self.elist(e))
                if t:
                    res = self.ifstop(e, r, text)
                    if res:
                        return res
                    else:
                        res = self.ifstart(e, r, text)
                        if res:
                            return res

            res = self.ifstart(e, r, text)
            if res:
                return res
            else:
                res = self.ifstop(e, r, text)
                if res:
                    return res
        return False

    def ifstart(self, e, r, text):
        if text in e.START:
            res = self.elem_init(e, r, text)
            return res
        return False

    def ifstop(self, e, r, text):
        if text in e.STOP:
            res = self.elem_close(e, r, text)
            return res
        return False

    def validate(self):
        is_valid = True
        for el in self.elements:
            for e in self.elist(el):
                if not e.is_closed():
                    is_valid = False
                    print('Warning: Page has en unclosed element of type %s at position %s, force closing at %s..' % (
                        e.__class__.__name__,
                        e.points[0],
                        e.points[0] + len(e.open_tag)
                    ))

                    try:
                        # try force closing
                        e.stop(e.points[0] + len(e.open_tag), '')
                        is_valid = True
                    except:
                        return False
        return is_valid

    def parse(self):

        def esc(tag):
            return r'%s' % (
                tag.replace('[', '\[')
                .replace(']', '\]')
                .replace('{', '\{')
                .replace('}', '\}')
                .replace('|', '\|')
                .replace('=', '\=')
            )

        v = self.view
        all_tags_regions = []
        for tag in sorted(self.tags, key=len, reverse=True):
            tags_regions = v.find_all(esc(tag), sublime.IGNORECASE)
            for t in all_tags_regions:
                _to_remove = []
                for _t in tags_regions:

                    # TODO: hacks exceptions
                    # '' will be not found in sequence '''''
                    # 1st will be found bold '''
                    # 2nd italic will be found twise '','' and last ' will be ignored
                    # fix this issue
                    if _t.size() == 3 and v.substr(_t) == "'''":
                        if v.substr(sublime.Region(_t.a, _t.b + 2)) == "'''''":
                            lost_italic = sublime.Region(_t.b, _t.b + 2)
                            if lost_italic not in tags_regions and not t.contains(_t):
                                # force to add italic region into tags list
                                # if this bold will not be ignored
                                tags_regions.append(lost_italic)
                    # ----------------------

                    if t.contains(_t):

                        # TODO: hacks exceptions
                        # in sequence like }}}}
                        # 1st wil be found }}} as TemplateAttribute tag
                        # last } will be ignored
                        # but we want to catch this as two template close tags }}, }}
                        if t.size() == 3 and v.substr(t) == "}}}" and v.substr(_t) == "}}":
                            if (v.substr(sublime.Region(t.a, t.b + 1)) == "}" * 4 and
                                    v.substr(sublime.Region(t.a, t.b + 2)) != "}" * 5):
                                continue
                        if t.size() == 3 and v.substr(t) == "{{{" and v.substr(_t) == "{{":
                            if (v.substr(sublime.Region(t.a, t.b + 1)) == "{" * 4 and
                                    v.substr(sublime.Region(t.a, t.b + 2)) != "}" * 5):
                                continue
                        # ---------------------

                        _to_remove.append(_t)

                    if self.debug and (t in self.debug_regions or _t in self.debug_regions):
                        print('%s%s %s %s%s' % (v.substr(t), t, 'contains' if t.contains(_t) else 'not contains', v.substr(_t), _t))

                for _r in _to_remove:
                    tags_regions.remove(_r)  # TODO: make intersect

                    if self.debug and _r in self.debug_regions:
                        print('%s%s removed' % (v.substr(_r), _r))

            all_tags_regions += tags_regions
        for tag_region in sorted(all_tags_regions, key=lambda x: x.a):
            self.markup(v.substr(tag_region), tag_region)

        return self.validate()
