from django_cradmin.viewhelpers import objecttable
from django_cradmin import crapp
from django_cradmin import crinstance
from django.utils.translation import ugettext_lazy as _

from devilry.apps.core.models import AssignmentGroup
from devilry.devilry_student.cradminextensions import studentobjecttable
from devilry.devilry_student.cradminextensions.columntypes import LastDeadlineColumn


class AssignmentInfoColumn(objecttable.SingleActionColumn):
    orderingfield = 'parentnode__long_name'
    template_name = 'django_cradmin/viewhelpers/objecttable/singleactioncolumn-cell.django.html'
    normalcells_css_classes = [
        'objecttable-cell-lg',
        'objecttable-cell-strong'
    ]

    def render_value(self, group):
        return group.parentnode.long_name

    def get_header(self):
        return _('Assignment')

    def get_actionurl(self, group):
        return crinstance.reverse_cradmin_url(
            instanceid='devilry_student_group',
            appname='deliveries',
            roleid=group.id,
            viewname='add-delivery')


class PeriodInfoColumn(objecttable.PlainTextColumn):
    """
    Period info column used for tablets and desktop devices.
    """
    orderingfield = 'parentnode__parentnode__parentnode__long_name'
    allcells_css_classes = ['hidden-xs']

    def get_header(self):
        return _('Course')

    def render_value(self, group):
        return u'{} - {}'.format(
            group.subject.long_name,
            group.period.long_name)


class PeriodInfoXs(objecttable.PlainTextColumn):
    """
    Period info column used for mobile devices.
    """
    orderingfield = 'parentnode__parentnode__parentnode__long_name'
    allcells_css_classes = ['visible-xs']

    def get_header(self):
        return _('Course')

    def render_value(self, group):
        return u'{} - {}'.format(
            group.subject.short_name,
            group.period.short_name)


class WaitingForDeliveriesListView(studentobjecttable.StudentObjectTableView):
    model = AssignmentGroup
    columns = [
        AssignmentInfoColumn,
        PeriodInfoColumn,
        PeriodInfoXs,
        LastDeadlineColumn
    ]

    def get_pagetitle(self):
        return _('Assignments open for delivery')

    def get_queryset_for_role(self, period):
        return AssignmentGroup.objects\
            .filter_student_has_access(self.request.user) \
            .filter_is_active() \
            .filter_can_add_deliveries() \
            .select_related(
                'parentnode',  # Assignment
                'parentnode__parentnode',  # Period
                'parentnode__parentnode__parentnode',  # Subject
            ) \
            .annotate_with_last_deadline_datetime()\
            .extra(
                order_by=['last_deadline_datetime']
            )


class App(crapp.App):
    appurls = [
        crapp.Url(
            r'^$',
            WaitingForDeliveriesListView.as_view(),
            name=crapp.INDEXVIEW_NAME),
    ]