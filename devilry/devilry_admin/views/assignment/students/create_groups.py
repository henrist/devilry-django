import logging

from crispy_forms import layout
from django import forms
from django.contrib import messages
from django.http import HttpResponseRedirect
from django.shortcuts import redirect
from django.utils.translation import pgettext_lazy
from django_cradmin import crapp
from django_cradmin.crispylayouts import PrimarySubmit
from django_cradmin.viewhelpers import formbase

from devilry.apps.core.models import Candidate, AssignmentGroup
from devilry.devilry_admin.cradminextensions.listbuilder import listbuilder_relatedstudent
from devilry.devilry_admin.cradminextensions.multiselect2 import multiselect2_relatedstudent

logger = logging.getLogger(__name__)


class ChooseMethod(formbase.FormView):
    template_name = 'devilry_admin/assignment/students/create_groups/choose-method.django.html'

    def dispatch(self, request, *args, **kwargs):
        self.assignment = self.request.cradmin_role
        self.period = self.assignment.parentnode
        return super(ChooseMethod, self).dispatch(request, *args, **kwargs)

    def __make_copy_from_assignment_choice(self, assignment):
        copy_passing_value = 'copy-passing-from-assignment-{}'.format(assignment.id)
        copy_passing_label = pgettext_lazy('admin create_groups',
                                           'Students with passing grade on %(assignment)s') % {
            'assignment': assignment.long_name
        }
        copy_all_value = 'copy-all-from-assignment-{}'.format(assignment.id)
        copy_all_label = pgettext_lazy('admin create_groups',
                                       'All students registered on %(assignment)s') % {
            'assignment': assignment.long_name
        }
        return (
            pgettext_lazy('admin create_groups', 'Copy from %(assignment)s') % {
                'assignment': assignment.long_name
            },
            (
                (copy_passing_value, copy_passing_label),
                (copy_all_value, copy_all_label),
            )
        )

    def get_other_assignments_in_period_method_choices(self):
        assignments = self.period.assignments\
            .order_by('-publishing_time')\
            .exclude(pk=self.assignment.pk)
        return [self.__make_copy_from_assignment_choice(assignment)
                for assignment in assignments]

    def get_method_choices(self):
        choices = [
            ('all-from-period', pgettext_lazy(
                    'admin create_groups',
                    'All students registered on %(semester)s') % {'semester': self.period.get_path()}),
            ('select-manually', pgettext_lazy(
                    'admin create_groups',
                    'Select manually'))
        ]
        choices.extend(self.get_other_assignments_in_period_method_choices())
        return choices

    def get_form_class(self):
        method_choices = self.get_method_choices()

        class SelectMethodForm(forms.Form):
            method = forms.ChoiceField(
                required=True,
                label=pgettext_lazy('devilry_admin create_groups', 'How would you like to add students?'),
                initial=method_choices[0][0],
                choices=method_choices
            )

        return SelectMethodForm

    def get_field_layout(self):
        return [
            layout.Div(
                'method',
                css_class='cradmin-globalfields')
        ]

    def get_buttons(self):
        return [
            PrimarySubmit('add-students',
                          pgettext_lazy('admin create_groups', 'Add students')),
        ]

    def form_valid(self, form):
        # ... do something with the form ...
        return HttpResponseRedirect('/some/view')


class RelatedStudentMultiselectTarget(multiselect2_relatedstudent.Target):
    def get_submit_button_text(self):
        return pgettext_lazy('admin create_groups',
                             'Add students')


class CreateGroupsViewMixin(object):
    form_invalid_message = pgettext_lazy(
        'admin create_groups',
        'Oups! Something went wrong. This may happen if someone edited '
        'students on the assignment or the semester while you were making '
        'your selection. Please try again.')

    def dispatch(self, request, *args, **kwargs):
        self.assignment = self.request.cradmin_role
        self.period = self.assignment.parentnode
        return super(CreateGroupsViewMixin, self).dispatch(request, *args, **kwargs)

    def __get_relatedstudents_in_group_on_assignment(self):
        assignment = self.request.cradmin_role
        return Candidate.objects.filter(assignment_group__parentnode=assignment)\
            .values_list('relatedstudent_id', flat=True)

    def get_unfiltered_queryset_for_role(self, role):
        queryset = self.period.relatedstudent_set\
            .select_related('user')\
            .exclude(pk__in=self.__get_relatedstudents_in_group_on_assignment())
        return queryset

    def post(self, request, *args, **kwargs):
        available_relatedstudents_queryset = self.get_unfiltered_queryset_for_role(
                role=self.request.cradmin_role)
        form = multiselect2_relatedstudent.SelectRelatedStudentsForm(
            data=self.request.POST,
            relatedstudents_queryset=available_relatedstudents_queryset)
        if form.is_valid():
            return self.form_valid(form)
        else:
            return self.form_invalid(form)

    def create_groups_with_candidate_and_feedbackset(self, relatedstudent_queryset):
        assignment = self.request.cradmin_role
        return AssignmentGroup.objects.bulk_create_groups(
            created_by_user=self.request.user,
            assignment=assignment,
            relatedstudents=list(relatedstudent_queryset))

    def form_valid(self, form):
        self.create_groups_with_candidate_and_feedbackset(
                relatedstudent_queryset=form.cleaned_data['selected_items'])
        return redirect(self.request.cradmin_instance.appindex_url('studentoverview'))

    def form_invalid(self, form):
        messages.error(self.request, self.form_invalid_message)
        logger.warning('%s.%s failed to validate. '
                       'This should not happen unless a user was removed '
                       'from the semester while the user selected students, '
                       'or if multiple admins edited/added students at the same time. '
                       'The user that experienced this error: %s (userid=%s). '
                       'Form validation error messages: %r',
                       self.__class__.__module__, self.__class__.__name__,
                       self.request.user.shortname,
                       self.request.user.id,
                       form.errors.as_data())
        # return redirect(self.request.cradmin_app.reverse_appindexurl())
        return redirect(self.request.cradmin_app.reverse_appurl('preview-and-confirm'))


class PreviewAndConfirmSelectedStudentsView(CreateGroupsViewMixin,
                                            listbuilder_relatedstudent.VerticalFilterListView):
    value_renderer_class = listbuilder_relatedstudent.ReadOnlyItemValue

    def get_pagetitle(self):
        return pgettext_lazy('admin create_groups',
                             'Confirm that you want to add the following students to %(assignment)s') % {
            'assignment': self.assignment.get_path()
        }

    def get_filterlist_url(self, filters_string):
        return self.request.cradmin_app.reverse_appurl(
            'preview-and-confirm',
            kwargs={'selected_students': self.kwargs['selected_students'],
                    'filters_string': filters_string})

    def get_unfiltered_queryset_for_role(self, role):
        queryset = super(PreviewAndConfirmSelectedStudentsView, self).get_unfiltered_queryset_for_role(role=role)
        # TODO: Filter according to selection
        return queryset


class ManualSelectStudentsView(CreateGroupsViewMixin,
                               listbuilder_relatedstudent.HorizontalFilterListView):
    """
    View used to manually select students when creating groups.
    """
    value_renderer_class = multiselect2_relatedstudent.ItemValue

    def get_pagetitle(self):
        return pgettext_lazy('admin create_groups',
                             'Select the students you want to add to %(assignment)s') % {
            'assignment': self.assignment.get_path()
        }

    def get_pageheading(self):
        return pgettext_lazy('admin create_groups',
                             'Select the students you want to add to %(assignment)s') % {
            'assignment': self.assignment.long_name
        }

    def get_filterlist_template_name(self):
        return 'devilry_admin/assignment/students/create_groups/manual-select-students.django.html'

    def get_filterlist_url(self, filters_string):
        return self.request.cradmin_app.reverse_appurl(
            'manual-select', kwargs={'filters_string': filters_string})

    def __get_multiselect_target(self):
        return RelatedStudentMultiselectTarget()

    def get_context_data(self, **kwargs):
        context = super(ManualSelectStudentsView, self).get_context_data(**kwargs)
        context['multiselect_target'] = self.__get_multiselect_target()
        return context


class App(crapp.App):
    appurls = [
        crapp.Url(r'^$', ChooseMethod.as_view(), name=crapp.INDEXVIEW_NAME),
        crapp.Url(r'^preview-and-confirm/(?P<selected_students>\w+)/(?P<filters_string>.+)?$',
                  PreviewAndConfirmSelectedStudentsView.as_view(),
                  name='preview-and-confirm'),
        crapp.Url(
            r'^manual-select/(?P<filters_string>.+)?$',
            ManualSelectStudentsView.as_view(),
            name='manual-select'),
    ]
