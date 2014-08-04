# -*- coding: UTF-8 -*-
# Copyright 2012-2014 Luc Saffre
# This file is part of the Lino project.
# Lino is free software; you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
# Lino is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
# You should have received a copy of the GNU Lesser General Public License
# along with Lino; if not, see <http://www.gnu.org/licenses/>.

from __future__ import unicode_literals
from __future__ import print_function

"""
The :xfile:`models.py` module for the :mod:`lino.modlib.courses` app.

Models:

Slot
Topic
Line
Course
Enrolment

"""

import logging
logger = logging.getLogger(__name__)

import datetime
from decimal import Decimal
ZERO = Decimal()
ONE = Decimal(1)

from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _
from django.utils.translation import pgettext_lazy as pgettext

# from north.dbutils import day_and_month

from lino import dd
from lino import mixins
from lino.utils.choosers import chooser

from ..contacts.utils import parse_name

config = settings.SITE.plugins.courses

users = dd.resolve_app('users')
cal = dd.resolve_app('cal')
sales = dd.resolve_app('sales')
contacts = dd.resolve_app('contacts')

"""
Here we must use `resolve_model` with `strict=True`
because we want the concrete model
and we don't know whether it is overridden
by this application.
"""
Person = dd.resolve_model('contacts.Person', strict=True)
# equivalent alternative :
#~ Person = settings.SITE.modules.contacts.Person


class StartEndTime(dd.Model):

    class Meta:
        abstract = True
    start_time = models.TimeField(
        blank=True, null=True,
        verbose_name=_("Start Time"))
    end_time = models.TimeField(
        blank=True, null=True,
        verbose_name=_("End Time"))


class Slot(mixins.Sequenced, StartEndTime):

    """
    """
    class Meta:
        verbose_name = _("Timetable Slot")  # Zeitnische
        verbose_name_plural = _('Timetable Slots')

    name = models.CharField(max_length=200,
                            blank=True,
                            verbose_name=_("Name"))

    def __unicode__(self):
        return self.name or "%s-%s" % (self.start_time, self.end_time)


class Slots(dd.Table):
    model = Slot
    required = dd.required(user_level='manager')
    insert_layout = """
    start_time end_time
    name
    """
    detail_layout = """
    name start_time end_time
    courses.CoursesBySlot
    """


class Topic(dd.BabelNamed, dd.Printable):

    class Meta:
        verbose_name = _("Topic")
        verbose_name_plural = _('Topics')


class Topics(dd.Table):
    model = Topic
    required = dd.required(user_level='manager')
    detail_layout = """
    id name
    courses.LinesByTopic
    courses.CoursesByTopic
    """


class Line(dd.BabelNamed):

    class Meta:
        verbose_name = _("Course Line")
        verbose_name_plural = _('Course Lines')
    topic = models.ForeignKey(Topic, blank=True, null=True)
    description = dd.BabelTextField(_("Description"), blank=True)

    every_unit = cal.Recurrencies.field(
        _("Recurrency"),
        default=cal.Recurrencies.per_weekday,
        blank=True)  # iCal:DURATION
    every = models.IntegerField(_("Repeat every"), default=1)

    event_type = dd.ForeignKey(
        'cal.EventType', null=True, blank=True,
        help_text=_("""The Event Type to which events will be generated."""))

    tariff = dd.ForeignKey('products.Product',
                           blank=True, null=True,
                           verbose_name=_("Participation fee"),
                           related_name='lines_by_tariff')

    guest_role = dd.ForeignKey(
        "cal.GuestRole", blank=True, null=True,
        help_text=_("Default guest role for particpants of events."))


class Lines(dd.Table):
    model = Line
    required = dd.required(user_level='manager')
    detail_layout = """
    id name
    event_type guest_role tariff every_unit every
    description
    courses.CoursesByLine
    """
    insert_layout = dd.FormLayout("""
    name
    every_unit every
    event_type guest_role tariff
    description
    """, window_size=(70, 16))


class LinesByTopic(Lines):
    master_key = "topic"


class EventsByTeacher(cal.Events):
    help_text = _("Shows events of courses of this teacher")
    master = config.teacher_model
    column_names = 'when_text:20 owner room state'
    # column_names = 'when_text:20 course__line room state'
    auto_fit_column_widths = True

    @classmethod
    def get_request_queryset(self, ar):
        teacher = ar.master_instance
        if teacher is None:
            return []
        if True:
            return []
        # TODO: build a list of courses, then show events by course
        qs = super(EventsByTeacher, self).get_request_queryset(ar)
        mycourses = dd.modules.Course.objects.filter(teacher=teacher)
        qs = qs.filter(course__in=teacher.course_set.all())
        return qs


class CourseStates(dd.Workflow):
    required = dd.required(user_level='admin')

add = CourseStates.add_item
add('10', _("Draft"), 'draft', editable=True)
#~ add('20', _("Published"),'published',editable=False)
add('20', _("Registered"), 'registered', editable=False)
add('30', _("Started"), 'started', editable=False)
add('40', _("Ended"), 'ended', editable=False)
add('50', _("Cancelled"), 'cancelled', editable=True)

#~ ACTIVE_COURSE_STATES = set((CourseStates.published,CourseStates.started))
ACTIVE_COURSE_STATES = set((CourseStates.registered, CourseStates.started))


class EnrolmentStates(dd.Workflow):
    verbose_name_plural = _("Enrolment states")
    required = dd.required(user_level='admin')
    invoiceable = models.BooleanField(_("invoiceable"), default=True)
    uses_a_place = models.BooleanField(_("Uses a place"), default=True)

add = EnrolmentStates.add_item
add('10', _("Requested"), 'requested', invoiceable=False, uses_a_place=False)
add('20', _("Confirmed"), 'confirmed', invoiceable=True, uses_a_place=True)
add('30', _("Cancelled"), 'cancelled', invoiceable=False, uses_a_place=False)
add('40', _("Certified"), 'certified', invoiceable=True, uses_a_place=True)
#~ add('40', _("Started"),'started')
#~ add('50', _("Success"),'success')
#~ add('60', _("Award"),'award')
#~ add('90', _("Abandoned"),'abandoned')


class Course(cal.Reservation, dd.Printable):
    """A Course is a group of pupils that regularily meet with a given
    teacher in a given room to speak about a given subject.

    The subject of a course is expressed by the :class:`Line`.

    """

    FILL_EVENT_GUESTS = False

    class Meta:
        abstract = settings.SITE.is_abstract_model('courses.Course')
        verbose_name = _("Course")
        verbose_name_plural = _('Courses')

    line = models.ForeignKey('courses.Line')
    teacher = models.ForeignKey(config.teacher_model, blank=True, null=True)
    #~ room = models.ForeignKey(Room,blank=True,null=True)
    slot = models.ForeignKey(Slot, blank=True, null=True)

    quick_search_fields = ('line__name', 'line__topic__name')

    state = CourseStates.field(default=CourseStates.draft)

    max_places = models.PositiveIntegerField(
        pgettext("in a course", "Places"),
        help_text=("Maximal number of participants"),
        blank=True, null=True)

    name = models.CharField(max_length=100,
                            blank=True,
                            verbose_name=_("Name"))
    duplicate = dd.Duplicate()

    def on_duplicate(self, ar, master):
        self.state = CourseStates.draft
        super(Course, self).on_duplicate(ar)

    def __unicode__(self):
        if self.name:
            return self.name
        if self.room is None:
            return "%s (%s)" % (self.line, dd.dtos(self.start_date))
        return u"%s (%s %s)" % (
            self.line,
            dd.dtos(self.start_date),
            self.room)

    def update_cal_from(self, ar):
        """Note: if recurrency is per_weekday, actual start may be
        later than self.start_date

        """
        # if self.state in (CourseStates.draft, CourseStates.cancelled):
        if self.state == CourseStates.cancelled:
            ar.info("No start date because state is %s", self.state)
            return None
        return self.start_date

    def update_cal_calendar(self):
        return self.line.event_type

    def update_cal_summary(self, i):
        return "%s %s" % (dd.babelattr(
            self.line.event_type, 'event_label'), i)

    def suggest_cal_guests(self, event):
        # logger.info("20140314 suggest_guests")
        Guest = dd.modules.cal.Guest
        if self.line is None:
            return
        gr = self.line.guest_role
        if gr is None:
            return
        fkw = dict(course=self)
        states = (EnrolmentStates.requested, EnrolmentStates.confirmed)
        fkw.update(state__in=states)
        for obj in Enrolment.objects.filter(**fkw):
            yield Guest(
                event=event,
                partner=obj.pupil,
                role=gr)

    def get_free_places(self):
        used = EnrolmentStates.filter(uses_a_place=True)
        qs = Enrolment.objects.filter(course=self, state__in=used)
        return self.max_places - qs.count()

    def full_clean(self, *args, **kw):
        if self.line is not None:
            if self.every_unit is None:
                self.every_unit = self.line.every_unit
            if self.every is None:
                self.every = self.line.every
        super(Course, self).full_clean(*args, **kw)

    def before_auto_event_save(self, event):
        """
        Sets room and start_time for automatic events.
        This is a usage example for
        :meth:`EventGenerator.before_auto_event_save
        <lino.modlib.cal.models.EventGenerator.before_auto_event_save>`.
        """
        #~ logger.info("20131008 before_auto_event_save")
        assert not settings.SITE.loading_from_dump
        assert event.owner == self
        #~ event = instance
        if event.is_user_modified():
            return
        #~ if event.is_fixed_state(): return
        #~ course = event.owner
        #~ event.project = self
        event.course = self
        event.room = self.room
        if self.slot:
            event.start_time = self.slot.start_time
            event.end_time = self.slot.end_time
        else:
            event.start_time = self.start_time
            event.end_time = self.end_time

    @dd.displayfield(_("Info"))
    def info(self, ar):
        return ar.obj2html(self)

    #~ @dd.displayfield(_("Where"))
    #~ def where_text(self,ar):
        # ~ return unicode(self.room) # .company.city or self.company)

    @dd.displayfield(_("Events"))
    def events_text(self, ar=None):
        return ', '.join([
            config.day_and_month(e.start_date)
            for e in self.events_by_course.order_by('start_date')])

    @property
    def events_by_course(self):
        ct = dd.ContentType.objects.get_for_model(self.__class__)
        return cal.Event.objects.filter(owner_type=ct, owner_id=self.id)

    @dd.requestfield(_("Requested"))
    def requested(self, ar):
        return EnrolmentsByCourse.request(
            self, param_values=dict(state=EnrolmentStates.requested))

    @dd.requestfield(_("Confirmed"))
    def confirmed(self, ar):
        return EnrolmentsByCourse.request(
            self, param_values=dict(state=EnrolmentStates.confirmed))

    @dd.requestfield(_("Enrolments"))
    def enrolments(self, ar):
        return EnrolmentsByCourse.request(self)


"""
customize fields coming from mixins to override their inherited default verbose_names
"""
dd.update_field(Course, 'every_unit', default=models.NOT_PROVIDED)
dd.update_field(Course, 'every', default=models.NOT_PROVIDED)


if Course.FILL_EVENT_GUESTS:

    @dd.receiver(dd.post_save, sender=cal.Event, dispatch_uid="fill_event_guests_from_course")
    def fill_event_guests_from_course(sender=None, instance=None, **kw):
        #~ logger.info("20130528 fill_event_guests_from_course")
        if settings.SITE.loading_from_dump:
            return
        event = instance
        if event.is_user_modified():
            return
        if event.is_fixed_state():
            return
        if not isinstance(event.owner, Course):
            return
        course = event.owner
        if event.guest_set.count() > 0:
            return
        for e in course.enrolment_set.all():
            cal.Guest(partner=e.pupil, event=event).save()


class CourseDetail(dd.FormLayout):
    #~ start = "start_date start_time"
    #~ end = "end_date end_time"
    #~ freq = "every every_unit"
    #~ start end freq
    main = "general courses.EnrolmentsByCourse"
    general = dd.Panel("""
    line teacher start_date end_date start_time end_time
    user room #slot workflow_buttons id:8
    max_places max_events max_date  every_unit every
    monday tuesday wednesday thursday friday saturday sunday
    cal.EventsByController
    """, label=_("General"))


class Courses(dd.Table):
    model = 'courses.Course'
    #~ order_by = ['date','start_time']
    detail_layout = CourseDetail()
    insert_layout = """
    start_date
    line teacher
    """
    column_names = "info line teacher room state *"
    # order_by = ['start_date']
    # order_by = 'line__name room__name start_date'.split()
    order_by = ['name']

    parameters = dd.ObservedPeriod(
        line=models.ForeignKey('courses.Line', blank=True, null=True),
        topic=models.ForeignKey('courses.Topic', blank=True, null=True),
        #~ company = models.ForeignKey('contacts.Company',blank=True,null=True),
        teacher=models.ForeignKey(
            config.teacher_model,
            blank=True, null=True),
        state=CourseStates.field(blank=True),
        active=dd.YesNo.field(blank=True),
    )
    params_layout = """topic line teacher state active"""

    simple_param_fields = 'line teacher state'.split()

    @classmethod
    def get_request_queryset(self, ar):
        qs = super(Courses, self).get_request_queryset(ar)
        if isinstance(qs, list):
            return qs
        for n in self.simple_param_fields:
            v = ar.param_values.get(n)
            if v:
                qs = qs.filter(**{n: v})
                #~ print(20130530, qs.query)

        if ar.param_values.topic:
            qs = qs.filter(line__topic=ar.param_values.topic)
        if ar.param_values.state is None:
            if ar.param_values.active == dd.YesNo.yes:
                qs = qs.filter(state__in=ACTIVE_COURSE_STATES)
            elif ar.param_values.active == dd.YesNo.no:
                qs = qs.exclude(state__in=ACTIVE_COURSE_STATES)
        return qs

    @classmethod
    def get_title_tags(self, ar):
        for t in super(Courses, self).get_title_tags(ar):
            yield t

        if ar.param_values.topic:
            yield unicode(ar.param_values.topic)
        for n in self.simple_param_fields:
            v = ar.param_values.get(n)
            if v:
                yield unicode(v)

    @classmethod
    def param_defaults(self, ar, **kw):
        kw = super(Courses, self).param_defaults(ar, **kw)
        #~ kw.update(state=CourseStates.started)
        kw.update(active=dd.YesNo.yes)
        return kw


class CoursesByTeacher(Courses):
    master_key = "teacher"
    column_names = "start_date start_time end_time line room *"
    order_by = ['start_date']


class CoursesByLine(Courses):
    master_key = "line"
    column_names = "info weekdays_text room times_text teacher *"
    order_by = ['room__name', 'start_date']


class CoursesByTopic(Courses):
    master = Topic
    order_by = ['start_date']
    column_names = "start_date:8 line:20 room:10 weekdays_text:10 times_text:10"

    @classmethod
    def get_request_queryset(self, ar):
        topic = ar.master_instance
        if topic is None:
            return []
        return settings.SITE.modules.courses.Course.objects.filter(
            line__topic=topic)


class CoursesBySlot(Courses):
    master_key = "slot"


class ActiveCourses(Courses):

    label = _("Active courses")
    #~ column_names = 'info requested confirmed teacher company room'
    column_names = 'info enrolments max_places teacher room *'
    #~ auto_fit_column_widths = True
    hide_sums = True


class CreateInvoiceForEnrolment(sales.CreateInvoice):

    def get_partners(self, ar):
        return [o.pupil for o in ar.selected_rows]


class Enrolment(dd.UserAuthored, dd.Printable, sales.Invoiceable):

    workflow_state_field = 'state'

    class Meta:
        abstract = settings.SITE.is_abstract_model('courses.Enrolment')
        verbose_name = _("Enrolment")
        verbose_name_plural = _('Enrolments')
        unique_together = ('course', 'pupil')

    #~ teacher = models.ForeignKey(Teacher)
    course = dd.ForeignKey('courses.Course')
    pupil = dd.ForeignKey(config.pupil_model)
    request_date = models.DateField(
        _("Date of request"), default=settings.SITE.today)
    state = EnrolmentStates.field(default=EnrolmentStates.requested)
    amount = dd.PriceField(_("Participation fee"), blank=True)
    remark = models.CharField(max_length=200,
                              blank=True,
                              verbose_name=_("Remark"))

    create_invoice = CreateInvoiceForEnrolment()

    @chooser()
    def pupil_choices(cls, course):
        Pupil = dd.resolve_model(config.pupil_model)
        return Pupil.objects.all()

    def create_pupil_choice(self, text):
        """
        Called when an unknown pupil name was given.
        Try to auto-create it.
        """
        Pupil = dd.resolve_model(config.pupil_model)
        kw = parse_name(text)
        if len(kw) != 2:
            raise ValidationError(
                "Cannot find first and last names in %r to \
                auto-create pupil", text)
        p = Pupil(**kw)
        p.full_clean()
        p.save()
        return p

    def get_confirm_veto(self, ar):
        """
        Called from ConfirmEnrolment.
        If this returns something else than None,
        then the enrolment won't be confirmed and the return value
        displayed to the user.
        """
        if self.course.max_places is None:
            return  # no veto. unlimited places.
        free = self.course.get_free_places()
        if free <= 0:
            return _("No places left in %s") % self.course
        #~ return _("Confirmation not implemented")

    def save(self, *args, **kw):
        if self.amount is None:
            self.compute_amount()
        super(Enrolment, self).save(*args, **kw)

    #~ def before_ui_save(self,ar):
        #~ if self.amount is None:
            #~ self.compute_amount()
        #~ super(Enrolment,self).before_ui_save(ar)

    def get_print_templates(self, bm, action):
        #~ if self.state:
        return [self.state.name + bm.template_ext]
        #~ return super(Enrolment,self).get_print_templates(bm,action)

    def __unicode__(self):
        return "%s / %s" % (self.course, self.pupil)

    invoiceable_date_field = 'request_date'
    #~ invoiceable_partner_field = 'pupil'

    @classmethod
    def get_partner_filter(cls, partner):
        q1 = models.Q(pupil__invoice_recipient__isnull=True, pupil=partner)
        q2 = models.Q(pupil__invoice_recipient=partner)
        return models.Q(q1 | q2, invoice__isnull=True)

    def pupil_changed(self, ar):
        self.compute_amount()

    def compute_amount(self):
        #~ if self.course is None:
            #~ return
        tariff = self.course.line.tariff
        # tariff is a DummyField when products is not installed
        # tariff may be None
        self.amount = getattr(tariff, 'sales_price', ZERO)
        # if tariff is None:
        #     self.amount = ZERO
        # else:
        #     self.amount = tariff.sales_price

    def get_invoiceable_amount(self):
        return self.amount

    def get_invoiceable_product(self):
        #~ if self.course is not None:
        if self.state.invoiceable:
            return self.course.line.tariff

    def get_invoiceable_title(self):
        #~ if self.course is not None:
        return self.course

    def get_invoiceable_qty(self):
        return ONE


class Enrolments(dd.Table):
    #~ debug_permissions=20130531
    required = dd.required(user_level='manager')
    model = 'courses.Enrolment'
    stay_in_grid = True
    parameters = dd.ObservedPeriod(
        author=dd.ForeignKey(
            settings.SITE.user_model, blank=True, null=True),
        state=EnrolmentStates.field(blank=True, null=True),
        course_state=CourseStates.field(
            _("Course state"), blank=True, null=True),
        participants_only=models.BooleanField(
            _("Participants only"),
            help_text=_(
                "Hide cancelled enrolments. "
                "Ignored if you specify an explicit enrolment state."),
            default=True),
    )
    params_layout = """start_date end_date author state course_state participants_only"""
    order_by = ['request_date']
    column_names = 'request_date course pupil workflow_buttons user *'
    #~ hidden_columns = 'id state'
    insert_layout = """
    request_date user
    course pupil
    remark
    """
    detail_layout = """
    request_date user
    course pupil
    remark amount workflow_buttons
    sales.InvoicingsByInvoiceable
    """

    @classmethod
    def get_request_queryset(self, ar):
        qs = super(Enrolments, self).get_request_queryset(ar)
        if isinstance(qs, list):
            return qs
        if ar.param_values.author is not None:
            qs = qs.filter(user=ar.param_values.author)

        if ar.param_values.state:
            qs = qs.filter(state=ar.param_values.state)
        else:
            if ar.param_values.participants_only:
                qs = qs.exclude(state=EnrolmentStates.cancelled)

        if ar.param_values.course_state:
            qs = qs.filter(course__state=ar.param_values.course_state)

        if ar.param_values.start_date is None or ar.param_values.end_date is None:
            period = None
        else:
            period = (ar.param_values.start_date, ar.param_values.end_date)
        if period is not None:
            qs = qs.filter(dd.inrange_filter('request_date', period))

        return qs

    @classmethod
    def get_title_tags(self, ar):
        for t in super(Enrolments, self).get_title_tags(ar):
            yield t

        if ar.param_values.state:
            yield unicode(ar.param_values.state)
        elif not ar.param_values.participants_only:
            yield unicode(_("Also ")) + unicode(EnrolmentStates.cancelled.text)
        if ar.param_values.course_state:
            yield unicode(
                settings.SITE.modules.courses.Course._meta.verbose_name) \
                + ' ' + unicode(ar.param_values.course_state)
        if ar.param_values.author:
            yield unicode(ar.param_values.author)


class ConfirmAllEnrolments(dd.Action):
    label = _("Confirm all")
    select_rows = False
    http_method = 'POST'

    def run_from_ui(self, ar, **kw):
        obj = ar.selected_rows[0]
        assert obj is None

        def ok(ar):
            for obj in ar:
                obj.state = EnrolmentStates.confirmed
                obj.save()
                ar.set_response(refresh_all=True)

        msg = _(
            "This will confirm all %d enrolments in this list.") % ar.get_total_count()
        ar.confirm(ok, msg, _("Are you sure?"))


class PendingRequestedEnrolments(Enrolments):

    label = _("Pending requested enrolments")
    auto_fit_column_widths = True
    params_panel_hidden = True
    column_names = 'request_date course pupil remark user amount workflow_buttons'
    hidden_columns = 'id state'

    confirm_all = ConfirmAllEnrolments()

    @classmethod
    def param_defaults(self, ar, **kw):
        kw = super(PendingRequestedEnrolments, self).param_defaults(ar, **kw)
        kw.update(state=EnrolmentStates.requested)
        return kw


class PendingConfirmedEnrolments(Enrolments):
    label = _("Pending confirmed enrolments")
    auto_fit_column_widths = True
    params_panel_hidden = True

    @classmethod
    def param_defaults(self, ar, **kw):
        kw = super(PendingConfirmedEnrolments, self).param_defaults(ar, **kw)
        kw.update(state=EnrolmentStates.confirmed)
        kw.update(course_state=CourseStates.ended)
        return kw


class EnrolmentsByPupil(Enrolments):
    params_panel_hidden = True
    required = dd.required()
    master_key = "pupil"
    column_names = 'request_date course user:10 remark amount:10 workflow_buttons *'

    @classmethod
    def param_defaults(self, ar, **kw):
        kw = super(EnrolmentsByPupil, self).param_defaults(ar, **kw)
        kw.update(participants_only=False)
        return kw

    insert_layout = """
    course
    remark
    request_date user
    """

from lino.utils import join_elems
from lino.utils.xmlgen.html import E

class EnrolmentsByCourse(Enrolments):
    params_panel_hidden = True
    required = dd.required()
    master_key = "course"
    column_names = 'request_date pupil_info user:10 remark amount:10 workflow_buttons *'
    auto_fit_column_widths = True
    # cell_edit = False

    insert_layout = """
    pupil
    remark
    request_date user
    """

    @dd.virtualfield(dd.HtmlBox(_("Participant")))
    def pupil_info(cls, self, ar):
        elems = [ar.obj2html(self.pupil, self.pupil.get_full_name())]
        elems += [', ']
        elems += join_elems(
            list(self.pupil.address_location_lines()),
            sep=', ')
        return E.div(*elems)


# class EventsByCourse(cal.Events):
#     required = dd.required(user_groups='office')
#     master_key = 'course'
#     column_names = 'when_text:20 linked_date summary workflow_buttons *'
#     auto_fit_column_widths = True


# dd.inject_field(
#     'cal.Event',
#     'course',
#     dd.ForeignKey(
#         'courses.Course',
#         blank=True, null=True,
#         help_text=_("Fill in only if this event is a session of a course."),
#         related_name="events_by_course"))


def setup_main_menu(site, ui, profile, main):
    m = main.add_menu("courses", config.verbose_name)
    m.add_action(Courses)
    m.add_action(PendingRequestedEnrolments)
    m.add_action(PendingConfirmedEnrolments)


def setup_config_menu(site, ui, profile, m):
    m = m.add_menu("courses", config.verbose_name)
    #~ m.add_action(Rooms)
    m.add_action(Topics)
    m.add_action(Lines)
    m.add_action(Slots)


def setup_explorer_menu(site, ui, profile, m):
    m = m.add_menu("courses", config.verbose_name)
    #~ m.add_action(Presences)
    #~ m.add_action(Events)
    m.add_action(Enrolments)
    m.add_action(EnrolmentStates)

dd.add_user_group('courses', config.verbose_name)
