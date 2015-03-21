# -*- coding: UTF-8 -*-
# Copyright 2014-2015 Luc Saffre
# License: BSD (see file COPYING for details)

"""Defines the :class:`Dupable` model mixin and related functionality
to assist users in finding duplicate database records.

Used by :mod:`lino.modlib.dupable_partners`.

The current implementation of the detection algorithm uses the `fuzzy
<https://pypi.python.org/pypi/Fuzzy>`_ module. Read also Doug Hellmann
about `Using Fuzzy Matching to Search by Sound with Python
<http://www.informit.com/articles/article.aspx?p=1848528>`_

Note about the name: to dupe *somebody* means "to make a dupe of;
deceive; delude; trick." (`reference.com
<http://dictionary.reference.com/browse/dupe>`_), while to dupe
*something* means to duplicate it (eventually in order to cheat
somebody e.g. by making a cheap copy of a valuable object).

"""

from __future__ import unicode_literals

import fuzzy

DMETA = fuzzy.DMetaphone()

from django.conf import settings
from django.db import models

from lino.api import dd, _
from lino.core.actions import SubmitInsert


def phonetic(s):
    # fuzzy.DMetaphone does not work with unicode strings, see
    # https://bitbucket.org/yougov/fuzzy/issue/2/fuzzy-support-for-unicode-strings-with
    dm = DMETA(s.encode('utf8'))
    dms = dm[0] or dm[1]
    if dms is None:
        return ''
    return dms.decode('utf8')
    # return fuzzy.nysiis(s)


class CheckedSubmitInsert(SubmitInsert):
    """Like the standard :class:`lino.core.actions.SubmitInsert`, but adds
    a confirmation if there is a possible duplicate record.

    """
    def run_from_ui(self, ar, **kw):
        obj = ar.create_instance_from_request()

        def ok(ar2):
            self.save_new_instance(ar2, obj)
            ar2.set_response(close_window=True)
            # logger.info("20140512 CheckedSubmitInsert")

        qs = obj.find_similar_instances(4)
        if len(qs) > 0:
            msg = _("There are %d similar %s:") % (
                len(qs), obj._meta.verbose_name_plural)
            for other in qs:
                msg += '<br/>\n' + unicode(other)

            msg += '<br/>\n'
            msg += _("Are you sure you want to create a new "
                     "%(model)s named %(name)s?") % dict(
                model=qs.model._meta.verbose_name,
                name=obj.get_full_name())

            ar.confirm(ok, msg)
        else:
            ok(ar)


class DupableWordBase(dd.Model):
    """Base class for the table of phonetic words of a given dupable
    model. For every (non-abstract) dupable model there must be a
    subclass of DupableWordBase. The subclass must define a field
    :attr:`owner` which points to the Dupable and set the
    :attr:`dupable_word_model`.

    """
    class Meta:
        abstract = True

    allow_cascaded_delete = ['owner']

    word = models.CharField(max_length=100)

    def __unicode__(self):
        return self.word


class Dupable(dd.Model):
    """Base class for models that can be "dupable".

    This mixin is to be used on models for which there is a danger of
    having unwanted duplicate records. It is both for *avoiding* such
    duplicates on new records and for *detecting* existing duplicates.

    """
    class Meta:
        abstract = True

    submit_insert = CheckedSubmitInsert()
    """A dupable model has its :attr:`submit_insert
    <lino.core.model.Model.submit_insert>` action overridden by
    :class:`CheckedSubmitInsert`, a extended variant of the action
    which checks for duplicate rows and asks a user confirmation when
    necessary.

    """

    dupable_words_field = 'name'
    """The name of a CharField on this model which holds the full-text
    description that is being tested for duplicates."""

    dupable_word_model = None
    """Full name of the model used to hold dupable words for instances of
    this model.  Applications can specify a string which will be
    resolved at startup to the model's class object.

    """

    @classmethod
    def on_analyze(cls, site):
        """Setup the :attr:`dupable_word_model` attribute.  This will be
        called only on concrete subclasses.

        """
        super(Dupable, cls).on_analyze(site)
        # if not site.is_installed(cls._meta.app_label):
        #     cls.dupable_word_model = None
        #     return
        site.setup_model_spec(cls, 'dupable_word_model')

    def dupable_matches_required(self):
        """Return the minimum number of words that must sound alike before
        two rows should be considered asimilar.
        
        """
        return 2

    def update_dupable_words(self, really=True):
        """Update the phonetic words of this row."""
        # "A related object set can be replaced in bulk with one
        # operation by assigning a new iterable of objects to it". But
        # only when the relatin is nullable...
        if settings.SITE.loading_from_dump:
            return
        if self.dupable_word_model is None:
            return
        qs = self.dupable_word_model.objects.filter(owner=self)
        existing = [o.word for o in qs]
        wanted = self.get_dupable_words(self.dupable_words_field)
        if existing == wanted:
            return
        if really:
            qs.delete()
            for w in wanted:
                self.dupable_word_model(word=w, owner=self).save()
        return _("Must update phonetic words.")

    def after_ui_save(self, ar, cw):
        super(Dupable, self).after_ui_save(ar, cw)
        if cw is None or cw.has_changed(self.dupable_words_field):
            self.update_dupable_words()

    def get_dupable_words(self, k):
        s = getattr(self, k)
        for c in '-,/&+':
            s = s.replace(c, ' ')
        return map(phonetic, s.split())

    def find_similar_instances(self, limit=None, **kwargs):
        """If `limit` is specified, we never want to see more than `limit`
        duplicates.

        Note that an overridden version of this method might return a
        list or tuple instead of a Django queryset.

        """
        if self.dupable_word_model is None:
            return self.__class__.objects.none()
        qs = self.__class__.objects.filter(**kwargs)
        if self.pk is not None:
            qs = qs.exclude(pk=self.pk)
        parts = self.get_dupable_words(self.dupable_words_field)
        qs = qs.filter(dupable_words__word__in=parts).distinct()
        qs = qs.annotate(num=models.Count('dupable_words__word'))
        qs = qs.filter(num__gte=self.dupable_matches_required())
        qs = qs.order_by('-num', 'pk')
        # print("20150306 find_similar_instances %s" % qs.query)
        if limit is None:
            return qs
        return qs[:limit]


from lino.modlib.plausibility.choicelists import Checker


class DupableChecker(Checker):
    """Checks for the following repairable problem:

    - :message:`Must update phonetic words.`

    """
    verbose_name = _("Check for missing phonetic words")
    model = Dupable
    
    def get_plausibility_problems(self, obj, fix=False):
        msg = obj.update_dupable_words(fix)
        if msg:
            yield (True, msg)

DupableChecker.activate()


class SimilarObjects(dd.VirtualTable):
    """Shows the other objects who are similar to this one."""
    # slave_grid_format = 'html'
    slave_grid_format = 'summary'

    class Row:

        def __init__(self, master, other):
            self.master = master
            self.other = other

        def summary_row(self, ar):
            yield ar.obj2html(self.other)

        def __unicode__(self):
            return unicode(self.other)

    @classmethod
    def get_data_rows(self, ar):
        mi = ar.master_instance
        if mi is None:
            return

        for o in mi.find_similar_instances(4):
            yield self.Row(mi, o)

    @dd.displayfield(_("Other"))
    def other(self, obj, ar):
        return ar.obj2html(obj.other)
