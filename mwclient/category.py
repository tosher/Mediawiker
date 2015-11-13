# -*- coding: utf-8 -*-

# from . import six
from .page import Page
from . import listing


class Category(Page, listing.GeneratorList):

    def __init__(self, site, name, info=None, namespace=None):
        Page.__init__(self, site, name, info)
        kwargs = {}
        kwargs['gcmtitle'] = self.name
        if namespace:
            kwargs['gcmnamespace'] = namespace
        listing.GeneratorList.__init__(self, site, 'categorymembers', 'cm', **kwargs)

    def __repr__(self):
        return "<Category object '%s' for %s>" % (self.name.encode('utf-8'), self.site)

    def members(self, prop='ids|title', namespace=None, sort='sortkey',
                dir='asc', start=None, end=None, generator=True):
        prefix = self.get_prefix('cm', generator)
        kwargs = dict(self.generate_kwargs(prefix, prop=prop, namespace=namespace,
                                           sort=sort, dir=dir, start=start, end=end, title=self.name))
        return self.get_list(generator)(self.site, 'categorymembers', 'cm', **kwargs)
