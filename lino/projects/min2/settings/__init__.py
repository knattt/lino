# -*- coding: UTF-8 -*-
# Copyright 2012-2015 Luc Saffre
# License: BSD (see file COPYING for details)
"""
Default settings for a `lino.projects.min2` application.
"""

from lino.projects.std.settings import *


class Site(Site):
    """The parent of all :mod:`lino.projects.min2` applications.
    """
    title = "Lino Mini 2"

    project_model = 'projects.Project'

    languages = 'en et'

    def get_installed_apps(self):
        yield super(Site, self).get_installed_apps()
        # yield 'lino.modlib.users'
        yield 'lino.modlib.changes'
        yield 'lino.modlib.excerpts'
        yield 'lino.projects.min2.modlib.contacts'
        yield 'lino.modlib.addresses'
        yield 'lino.modlib.reception'
        yield 'lino.modlib.iban'
        yield 'lino.modlib.sepa'
        yield 'lino.modlib.notes'
        yield 'lino.modlib.projects'
        yield 'lino.modlib.humanlinks'
        yield 'lino.modlib.households'
        yield 'lino.modlib.extensible'
        yield 'lino.modlib.pages'
        yield 'lino.modlib.export_excel'
        yield 'lino.modlib.dupable_partners'
        yield 'lino.modlib.plausibility'
        yield 'lino.modlib.tinymce'

    def setup_user_profiles(self):
        """
        Defines a set of user profiles.
        """
        from django.utils.translation import ugettext_lazy as _
        from lino.modlib.users.choicelists import UserProfiles

        from lino.core.roles import Anonymous, SiteAdmin
        from lino.modlib.office.roles import OfficeUser, OfficeStaff

        class SiteUser(OfficeUser):
            pass

        class SiteAdmin(SiteAdmin, OfficeStaff):
            pass

        UserProfiles.clear()
        add = UserProfiles.add_item
        add('000', _("Anonymous"), Anonymous, name='anonymous',
            readonly=True,
            authenticated=False)
        add('100', _("User"), SiteUser, name='user')
        add('900', _("Administrator"), SiteAdmin, name='admin')

