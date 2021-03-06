# -*- coding: UTF-8 -*-
# Copyright 2016 Luc Saffre
# License: BSD (see file COPYING for details)

from django.conf import settings
from lino.api import dd, rt, _
from lino.utils.xmlgen.html import E


class ChangeObservable(dd.Model):
    """Mixin for models which can emit notifications to a list of
    "observers" when an instance is modified.

    """

    class Meta(object):
        abstract = True

    def get_notify_message(self, ar, cw):
        if cw is None:
            return
        items = list(cw.get_updates_html())
        if len(items) == 0:
            return
        elems = [E.p(
            ar.obj2html(self),
            ' ', _("has been modified by {user}").format(
                user=ar.get_user()),
            ":")]
        elems.append(E.ul(*items))
        if False:
            elems.append(E.p(_(
                "Subsequent changes to {obj} will not be notified "
                "until you visit {url} and mark this notification "
                "as seen.").format(
                url=settings.SITE.server_url or "Lino",
                obj=self.get_notify_owner(ar))))
        return E.tostring(E.div(*elems))

    def get_notify_owner(self, ar):
        """Return the owner (the target database object) of the notification
        to create.

        For example comments.Comment overrides this.

        """
        return self

    def get_change_observers(self):
        """Return or yield a list of users who are observing changes on this
        object.

        Should be implemented in subclasses. The default
        implementation returns an empty list, i.e. nobody gets
        notified.

        """
        return []

    # def emit_message(self, ar, owner, subject, body):
    #     return super(ChangeObservable, self).emit_message(
    #         ar, owner, subject, body, self.get_notify_observers())

    def after_ui_save(self, ar, cw):

        super(ChangeObservable, self).after_ui_save(ar, cw)

        msg = self.get_notify_message(ar, cw)
        if not msg:
            return
        # subject, body = msg
        owner = self.get_notify_owner(ar)
        mt = rt.models.notify.MessageTypes.change
        rt.models.notify.Message.emit_message(
            ar, owner, mt, msg, self.get_change_observers())
