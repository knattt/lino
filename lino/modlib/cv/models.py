# -*- coding: UTF-8 -*-
# Copyright 2008-2015 Luc Saffre
# License: BSD (see file COPYING for details)

"""Database models for `lino.modlib.cv`.

.. autosummary::

- A **Language knowledge** is when a given person knows a given language.

- An **education** entry (fr: Éducation, de: Bildung) is when a given
  person has followed lessons in a given *school* for a given
  *period*.  There are two basic types of education: **studies** (fr:
  Études, de: Studium) and **trainings** (fr: Formation, de:
  Ausbildung).

- A **Work experience** (fr: Expérience professionnelle, de:
  Berufserfahrung) is when a given person has worked in a given
  *organisation* for a given *period*.

.. contents::
   :local:
   :depth: 2

"""

from __future__ import unicode_literals

from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.utils.translation import pgettext_lazy as pgettext

from lino.api import dd, rt
from lino import mixins
from lino.modlib.countries.mixins import CountryCity


from .mixins import (SectorFunction, PersonHistoryEntry,
                     HistoryByPerson, CefLevel, HowWell,
                     EducationEntryStates)

config = dd.plugins.cv


##
## Language knowledge
##

class LanguageKnowledge(dd.Model):
    """
    Specifies how well a certain Person knows a certain Language.
    """
    class Meta:
        verbose_name = _("language knowledge")
        verbose_name_plural = _("language knowledges")

    allow_cascaded_delete = ['person']

    person = models.ForeignKey(config.person_model)
    language = dd.ForeignKey("languages.Language")
    spoken = HowWell.field(_("Spoken"), blank=True)
    written = HowWell.field(_("Written"), blank=True)
    spoken_passively = HowWell.field(_("Spoken (passively)"),
                                     blank=True)
    written_passively = HowWell.field(_("Written (passively)"),
                                      blank=True)
    native = models.BooleanField(_("native language"), default=False)
    cef_level = CefLevel.field(blank=True)  # ,null=True)

    def __unicode__(self):
        if self.language_id is None:
            return ''
        if self.cef_level:
            return u"%s (%s)" % (self.language, self.cef_level)
        if self.spoken > '1' and self.written > '1':
            return _(u"%s (s/w)") % self.language
        elif self.spoken > '1':
            return _(u"%s (s)") % self.language
        elif self.written > '1':
            return _(u"%s (w)") % self.language
        else:
            return unicode(self.language)


class LanguageKnowledges(dd.Table):
    model = LanguageKnowledge
    required = config.get_default_required(user_level='manager')


class LanguageKnowledgesByPerson(LanguageKnowledges):
    master_key = 'person'
    #~ label = _("Language knowledge")
    #~ button_label = _("Languages")
    column_names = "language native spoken written cef_level"
    required = config.get_default_required()
    auto_fit_column_widths = True


class KnowledgesByLanguage(LanguageKnowledges):
    master_key = 'language'
    column_names = "person native spoken written cef_level"
    required = config.get_default_required()


##
## Education
##

class EducationEntry(PersonHistoryEntry, CountryCity):
    "Abstract base class for :class:`Training` and :class:`Study`."
    class Meta:
        abstract = True

    language = dd.ForeignKey("languages.Language", blank=True, null=True)

    school = models.CharField(_("Establishment"), max_length=200, blank=True)

    state = EducationEntryStates.field(blank=True)

    remarks = models.TextField(
        blank=True, null=True, verbose_name=_("Remarks"))

    type = models.ForeignKey('cv.StudyType')


class StudyOrTraining(dd.Model):

    class Meta:
        abstract = True

    is_study = models.BooleanField(_("Study"), default=True)
    is_training = models.BooleanField(_("Training"), default=False)


class EducationLevel(StudyOrTraining, mixins.BabelNamed, mixins.Sequenced):

    class Meta:
        verbose_name = _("Education Level")
        verbose_name_plural = _("Education Levels")


class EducationLevels(dd.Table):
    """The default table showing all :class:`EducationLevel` instances.
    """

    required = config.get_default_required(user_level='manager')
    model = 'cv.EducationLevel'
    column_names = 'name is_study is_training*'
    order_by = ['name']
    detail_layout = """
    name is_study is_training
    StudyTypesByLevel
    StudiesByLevel
    """


class StudyType(StudyOrTraining, mixins.BabelNamed):
    """The **Education Type** of a study or training is a way to group
    entries according to their type.

    TODO: Rename this to `EducationType`.

    Also used in :attr:`isip.Contract.study_type
    <lino_welfare.modlib.isip.models.Contract.study_type>` and by
    :attr:`EducationEntry.type`.

    .. attribute:: education_level

        Pointer to the :class:`EducationLevel`.

    .. attribute:: study_regime

        One choice from :class:`StudyRegimes`.

    """
    class Meta:
        verbose_name = _("Education Type")
        verbose_name_plural = _("Education Types")

    education_level = dd.ForeignKey(
        'cv.EducationLevel',
        null=True, blank=True)


class StudyTypes(dd.Table):
    """The default table showing all :class:`StudyType` instances.
    """
    required = config.get_default_required(user_level='admin')
    model = StudyType
    order_by = ["name"]
    detail_layout = """
    name id
    education_level is_study is_training
    cv.StudiesByType
    """

    insert_layout = """
    name
    is_study is_training
    education_level
    """


class StudyTypesByLevel(StudyTypes):
    master_key = 'education_level'


##
## Trainings
##

class Training(EducationEntry):

    class Meta:
        verbose_name = _("Training")
        verbose_name_plural = _("Trainings")

    content = models.CharField(
        max_length=200,
        blank=True,
        verbose_name=_("Training content"))

    certificates = models.CharField(
        max_length=200,
        blank=True,  # null=True,
        verbose_name=_("Certificates"))

    def __unicode__(self):
        return unicode(self.type)

    @dd.chooser()
    def type_choices(cls):
        return rt.modules.cv.StudyType.objects.filter(is_training=True)


class Trainings(dd.Table):
    """The default table showing all :class:`Trainings` instances.

    """

    required = config.get_default_required(user_level='manager')
    model = 'cv.Training'
    order_by = "country city type".split()

    detail_layout = """
    person start_date end_date
    type state #success certificates
    school country city
    remarks
    """


class TrainingsByCountry(Trainings):
    required = config.get_default_required()
    master_key = 'country'


class TrainingsByType(Trainings):
    required = config.get_default_required()
    master_key = 'type'


class TrainingsByPerson(HistoryByPerson, Trainings):
    required = config.get_default_required()
    column_names = 'type content start_date end_date \
    school country state certificates *'
    auto_fit_column_widths = True


##
## Studies
##

class Study(EducationEntry):

    class Meta:
        verbose_name = _("Study")
        verbose_name_plural = _("Studies")

    education_level = dd.ForeignKey(
        'cv.EducationLevel',
        null=True, blank=True)

    content = models.CharField(
        max_length=200,
        blank=True,
        verbose_name=_("Study content"))

    # success = models.BooleanField(verbose_name=_("Success"), default=False)

    def __unicode__(self):
        return unicode(self.type)

    @dd.chooser()
    def type_choices(cls):
        return rt.modules.cv.StudyType.objects.filter(is_study=True)


class Studies(dd.Table):
    """The default table showing all :class:`Study` instances.
    """

    required = config.get_default_required(user_level='manager')
    model = 'cv.Study'
    order_by = "country city type content".split()

    detail_layout = """
    person start_date end_date
    type content education_level state #success
    school country city
    remarks
    """


class StudiesByCountry(Studies):
    required = config.get_default_required()
    master_key = 'country'


class StudiesByLevel(Studies):
    required = config.get_default_required()
    master_key = 'education_level'


class StudiesByPlace(Studies):
    """
    Lists all Studies in a given Place.
    Used as slave grid in Places detail.
    """
    required = config.get_default_required()
    master_key = 'city'
    column_names = 'school type person content start_date end_date \
    state language remarks *'


class StudiesByType(Studies):
    required = config.get_default_required()
    master_key = 'type'
    column_names = 'school person content start_date end_date \
    state language remarks *'


class StudiesByPerson(HistoryByPerson, Studies):
    required = config.get_default_required()
    column_names = 'type content start_date end_date school country \
    state education_level *'
    auto_fit_column_widths = True


## Work Experiences


class Status(mixins.BabelNamed):

    class Meta:
        verbose_name = pgettext("work experience", "Status")
        verbose_name_plural = pgettext("work experience", 'Statuses')


class Statuses(dd.Table):
    """The default table showing all :class:`Status` instances.
    """
    required = config.get_default_required(user_level='manager')
    model = 'cv.Status'
    order_by = ['name']

    detail_layout = """
    id name
    ExperiencesByStatus
    """


class Regime(mixins.BabelNamed):
    # e.g. "38h/week"
    class Meta:
        verbose_name = _("Work Regime")
        verbose_name_plural = _('Work Regimes')


class Regimes(dd.Table):
    """The default table showing all :class:`Regime` instances.
    """
    required = config.get_default_required(user_level='manager')
    model = 'cv.Regime'
    order_by = ['name']
    detail_layout = """
    id name
    ExperiencesByRegime
    """


class Duration(mixins.BabelNamed):
    class Meta:
        verbose_name = _("Contract Duration")
        verbose_name_plural = _('Contract Durations')


class Durations(dd.Table):
    """The default table showing all :class:`Duration` instances.
    """
    required = config.get_default_required(user_level='manager')
    model = 'cv.Duration'
    order_by = ['name']
    detail_layout = """
    id name
    ExperiencesByDuration
    """


class Sector(mixins.BabelNamed):

    class Meta:
        verbose_name = _("Job Sector")
        verbose_name_plural = _('Job Sectors')

    remark = models.TextField(
        blank=True,
        verbose_name=_("Remark"))


class Sectors(dd.Table):
    """The default table showing all :class:`Sector` instances.
    """
    required = config.get_default_required(user_level='manager')
    model = Sector
    order_by = ['name']
    detail_layout = """
    id name
    remark FunctionsBySector
    cv.ExperiencesBySector
    """


class Function(mixins.BabelNamed):

    """Each Job may have a Function."""
    class Meta:
        verbose_name = _("Job Function")
        verbose_name_plural = _('Job Functions')

    remark = models.TextField(
        blank=True,
        verbose_name=_("Remark"))

    sector = models.ForeignKey(Sector)
        #~ related_name="%(app_label)s_%(class)s_set_by_provider",
        #~ verbose_name=_("Job Provider"),
        #~ blank=True,null=True)


class Functions(dd.Table):
    """The default table showing all :class:`Function` instances.
    """
    #~ debug_permissions = 20130704
    required = config.get_default_required(user_level='manager')
    model = 'cv.Function'
    column_names = 'name sector *'
    order_by = ['name']
    detail_layout = """
    id name sector
    remark
    cv.ExperiencesByFunction
    """


class FunctionsBySector(Functions):
    master_key = 'sector'


class Experience(PersonHistoryEntry, SectorFunction, CountryCity):
    """A **work experience** is when a given person has worked for a given
    period in a given company.

    """
    class Meta:
        verbose_name = _("Job Experience")
        verbose_name_plural = _("Job Experiences")
        get_latest_by = 'start_date'

    company = models.CharField(max_length=200, verbose_name=_("company"))
    #~ type = models.ForeignKey(JobType,verbose_name=_("job type"))
    title = models.CharField(
        max_length=200, verbose_name=_("job title"), blank=True)
    status = dd.ForeignKey('cv.Status', blank=True, null=True)
    duration = dd.ForeignKey('cv.Duration', blank=True, null=True)
    regime = dd.ForeignKey('cv.Regime', blank=True, null=True)
    is_training = models.BooleanField(_("Training"), default=False)

    remarks = models.TextField(_("Remarks"), blank=True, null=True)

    termination_reason = models.CharField(
        max_length=200,
        blank=True,  # null=True,
        verbose_name=_("Termination reason"))

    def __unicode__(self):
        return unicode(self.title)


class Experiences(dd.Table):
    """The default table showing all :class:`Experience` instances.
    """
    required = config.get_default_required(user_level='manager')
    model = 'cv.Experience'
    # stay_in_grid = True
    detail_layout = """
    person start_date end_date termination_reason
    company country city
    sector function title
    status duration regime is_training
    remarks
    """


class ExperiencesBySector(Experiences):
    required = config.get_default_required()
    master_key = 'sector'
    order_by = ["start_date"]


class ExperiencesByFunction(Experiences):
    required = config.get_default_required()
    master_key = 'function'
    order_by = ["start_date"]


class ExperiencesByPerson(HistoryByPerson, Experiences):
    required = config.get_default_required()
    auto_fit_column_widths = True
    column_names = "company country start_date end_date function \
    status duration termination_reason remarks *"


class ExperiencesByStatus(Experiences):
    master_key = 'status'
    column_names = "company country start_date end_date title sector \
    function regime remarks"


class ExperiencesByRegime(Experiences):
    master_key = 'regime'
    column_names = "company start_date end_date title sector \
    function country remarks"


class ExperiencesByDuration(Experiences):
    master_key = 'duration'
    column_names = "company start_date end_date title sector \
    function country remarks"


@dd.receiver(dd.post_analyze)
def set_detail_layouts(sender=None, **kwargs):
    rt.modules.languages.Languages.set_detail_layout("""
    id iso2 name
    cv.KnowledgesByLanguage
    """)


