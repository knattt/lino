# -*- coding: UTF-8 -*-
# Copyright 2015 Luc Saffre
# License: BSD (see file COPYING for details)

import datetime

from lino.api import dd
from lino.utils import ONE_DAY
SEVEN_DAYS = datetime.timedelta(days=7)
from lino.utils.xmlgen.html import E
from lino.modlib.cal.utils import Weekdays

REPORTERS = []


def add_reporter(r):
    assert not r in REPORTERS
    REPORTERS.append(r)


def get_report(ar, today=None, weeksback=1, weeksforth=0, datefmt=dd.fds):
    if not ar.user.profile.authenticated:
        return E.p()
    if today is None:
        today = dd.today()
    start_date = today - ONE_DAY * today.weekday() - weeksback * SEVEN_DAYS
    numweeks = weeksback + weeksforth + 1
    days = dict()
    cd = start_date
    numdays = numweeks * 7
    for i in range(numdays):
        days[cd] = []
        cd += ONE_DAY
    end_date = cd

    for r in REPORTERS:
        r(days, ar, start_date, end_date)
    headers = [E.th(Weekdays.choices[i][1], **ar.cellattrs) for i in range(7)]
    rows = [E.tr(*headers)]
    cd = start_date
    for week in range(numweeks):
        week = []
        for weekday in range(7):
            chunks = days[cd]
            chunks.insert(0, datefmt(cd))
            week.append(E.td(*chunks, **ar.cellattrs))
            cd += ONE_DAY
        rows.append(E.tr(*week))
    # print 20150420, rows
    return E.table(*rows, **ar.tableattrs)