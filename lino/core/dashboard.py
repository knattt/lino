# -*- coding: UTF-8 -*-
# Copyright 2016 Luc Saffre.
# License: BSD, see LICENSE for more details.
"""Lino's user preferences registry.

"""
from __future__ import unicode_literals

import six
from builtins import object
from django.conf import settings

from lino.api import _
from lino.core.permissions import Permittable
from lino.utils.xmlgen.html import E
from lino.core.actors import Actor

class DashboardItem(Permittable):
    """Base class for all dashboard items.

    .. attribute:: name

        The name used to reference this item in
        :attr:`Widget.item_name`.

    .. attribute:: width

        The width in percent of total available width.

    """

    width = None
    
    def __init__(self, name):
        self.name = name
        
    def render(self, ar):
        """Return a HTML string """

class ActorItem(DashboardItem):
    """The only one that's being used.

    See :mod:`lino_xl.lib.blogs` as a usage example.

    """
    def __init__(self, actor, header_level=2):
        self.actor = actor
        self.header_level = header_level
        super(ActorItem, self).__init__(str(actor))
        
    def get_view_permission(self, profile):
        return self.actor.default_action.get_view_permission(profile)

    def render(self, ar):
        T = self.actor
        sar = ar.spawn(T, limit=T.preview_limit)
        if sar.get_total_count():
            if self.header_level is None:
                s = ''
            else:
                s = E.tostring(E.h2(
                    T.label, ' ', ar.window_action_button(
                        T.default_action,
                        label="🗗",
                        style="text-decoration:none; font-size:80%;",
                        title=_("Show this table in own window"))))

            s += E.tostring(ar.show(sar))
            return s
            

class CustomItem(DashboardItem):
    """Won't work. Not used and not tested."""
    def __init__(self, name, func, *args, **kwargs):
        self.func = func
        self.args = args
        self.kwargs = kwargs
        super(CustomItem, self).__init__(name)
        
    def render(self, ar):
        return self.func(ar, *self.args, **self.kwargs)
                          
