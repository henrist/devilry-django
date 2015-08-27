from django.contrib import messages
from django.contrib.auth import get_user_model
from django import forms
from django.http import HttpResponseRedirect
from django.views.generic.edit import BaseFormView

from django_cradmin import crapp
from django_cradmin.viewhelpers import objecttable
from django.db import models
from django.utils.translation import ugettext_lazy as _
from django_cradmin.viewhelpers import delete

from devilry.apps.core.models import RelatedStudent
from devilry.devilry_account.models import UserEmail
from devilry.devilry_admin.views.common import userselect_common


class GetQuerysetForRoleMixin(object):
    model = RelatedStudent

    def get_queryset_for_role(self, role):
        period = role
        return self.model.objects \
            .filter(period=period) \
            .order_by('user__shortname')


class InfoColumn(objecttable.MultiActionColumn):
    modelfield = 'id'
    template_name = 'devilry_admin/common/user-info-column.django.html'

    def get_header(self):
        return _('Students')

    def get_buttons(self, obj):
        return [
            objecttable.Button(
                label=_('Remove'),
                url=self.reverse_appurl('remove', args=[obj.id]),
                buttonclass="btn btn-danger btn-sm devilry-relatedstudentlist-remove-button"),
        ]

    def get_context_data(self, obj):
        context = super(InfoColumn, self).get_context_data(obj=obj)
        context['user'] = obj.user
        return context


class ListView(GetQuerysetForRoleMixin, objecttable.ObjectTableView):
    searchfields = ['user__shortname', 'user__fullname']
    hide_column_headers = True
    columns = [InfoColumn]

    def get_buttons(self):
        app = self.request.cradmin_app
        return [
            objecttable.Button(label=_('Add student'),
                               url=app.reverse_appurl('select-user-to-add-as-student'),
                               buttonclass='btn btn-primary'),
        ]

    def get_pagetitle(self):
        return _('Students')

    def get_queryset_for_role(self, role):
        return super(ListView, self).get_queryset_for_role(role) \
            .prefetch_related(
            models.Prefetch('user__useremail_set',
                            queryset=UserEmail.objects.filter(is_primary=True),
                            to_attr='primary_useremail_objects'))


class RemoveView(GetQuerysetForRoleMixin, delete.DeleteView):
    """
    View used to remove students from a period.
    """

    def get_queryset_for_role(self, role):
        queryset = super(RemoveView, self) \
            .get_queryset_for_role(role=role)
        if not self.request.user.is_superuser:
            queryset = queryset.exclude(user=self.request.user)
        return queryset

    def get_object(self, *args, **kwargs):
        if not hasattr(self, '_object'):
            self._object = super(RemoveView, self).get_object(*args, **kwargs)
        return self._object

    def get_pagetitle(self):
        return _('Remove %(what)s') % {'what': self.get_object().user.get_full_name()}

    def get_success_message(self, object_preview):
        relatedstudent = self.get_object()
        period = relatedstudent.period
        user = relatedstudent.user
        return _('%(user)s is no longer student for %(what)s.') % {
            'user': user.get_full_name(),
            'what': period.get_path(),
        }

    def get_confirm_message(self):
        relatedstudent = self.get_object()
        period = relatedstudent.period
        user = relatedstudent.user
        return _('Are you sure you want to remove %(user)s as student for %(what)s?') % {
            'user': user.get_full_name(),
            'what': period.get_path(),
        }

    def get_action_label(self):
        return _('Remove')


class UserInfoColumn(userselect_common.UserInfoColumn):
    modelfield = 'shortname'
    select_label = _('Add as student')


class UserSelectView(userselect_common.AbstractUserSelectView):
    columns = [
        UserInfoColumn,
    ]

    def get_pagetitle(self):
        return _('Please select the user you want to add as students for %(what)s') % {
            'what': self.request.cradmin_role.long_name
        }

    def get_form_action(self):
        return self.request.cradmin_app.reverse_appurl('add-user-as-student')

    def get_excluded_user_ids(self):
        period = self.request.cradmin_role
        return period.relatedstudent_set.values_list('user_id', flat=True)


class AddView(BaseFormView):
    """
    View used to add a RelatedStudent to a Period.
    """
    http_method_names = ['post']

    model = RelatedStudent

    def get_form_class(self):
        period = self.request.cradmin_role
        userqueryset = get_user_model().objects \
            .exclude(pk__in=period.relatedstudent_set.values_list('user_id', flat=True))

        class AddAdminForm(forms.Form):
            user = forms.ModelChoiceField(
                queryset=userqueryset)
            next = forms.CharField(required=False)

        return AddAdminForm

    def __make_user_student(self, user):
        period = self.request.cradmin_role
        self.model.objects.create(user=user,
                                  period=period)

    def form_valid(self, form):
        user = form.cleaned_data['user']
        self.__make_user_student(user)

        period = self.request.cradmin_role
        successmessage = _('%(user)s added as student for %(what)s.') % {
            'user': user.get_full_name(),
            'what': period,
        }
        messages.success(self.request, successmessage)

        if form.cleaned_data['next']:
            nexturl = form.cleaned_data['next']
        else:
            nexturl = self.request.cradmin_app.reverse_appindexurl()
        return HttpResponseRedirect(nexturl)

    def form_invalid(self, form):
        messages.error(self.request,
                       _('Error: The user may not exist, or it may already be student.'))
        return HttpResponseRedirect(self.request.cradmin_app.reverse_appindexurl())


class App(crapp.App):
    appurls = [
        crapp.Url(r'^$', ListView.as_view(), name=crapp.INDEXVIEW_NAME),
        crapp.Url(
            r'^remove/(?P<pk>\d+)$',
            RemoveView.as_view(),
            name="remove"),
        crapp.Url(
            r'^select-user-to-add-as-student$',
            UserSelectView.as_view(),
            name="select-user-to-add-as-student"),
        crapp.Url(
            r'^add',
            AddView.as_view(),
            name="add-user-as-student"),
    ]