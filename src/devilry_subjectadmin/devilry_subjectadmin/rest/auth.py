"""
Re-usable authentification methods.
"""

from django.utils.translation import ugettext as _
from devilry.apps.core.models import (Subject,
                                      Period,
                                      Assignment)
from djangorestframework.permissions import BasePermission
from errors import PermissionDeniedError


def _admin_required(nodecls, user, errormsg, objid):
    if user.is_superuser:
        return
    if objid == None:
        raise PermissionDeniedError(errormsg)
    if nodecls.where_is_admin(user).filter(id=objid).count() == 0:
        raise PermissionDeniedError(errormsg)


def _subjectadmin_required(user, subjectid):
    """
    Raise :exc:`devilry_subjectadmin.rest.errors.PermissionDeniedError` unless
    the given ``user`` is admin on all of the given Subjects.

    :param subjectid: ID of Subject to check.
    """
    _admin_required(Subject, user, _('Permission denied'),  subjectid)


def periodadmin_required(user, periodid):
    """
    Raise :exc:`devilry_subjectadmin.rest.errors.PermissionDeniedError` unless
    the given ``user`` is admin on all of the given Periods.

    :param periodid: ID of Periods to check.
    """
    _admin_required(Period, user, _('Permission denied'), periodid)


def _assignmentadmin_required(user, assignmentid):
    """
    Raise :exc:`devilry_subjectadmin.rest.errors.PermissionDeniedError` unless
    the given ``user`` is admin on all of the given Assignments.

    :param assignmentid: ID of Assignment to check.
    """
    _admin_required(Assignment, user, _('Permission denied'), assignmentid)


class IsSubjectAdmin(BasePermission):
    """
    Djangorestframework permission checker that checks if the requesting user
    has admin-permissions on the subject given as the first argument to the
    view.
    """
    def check_permission(self, user):
        if len(self.view.args) != 1:
            raise PermissionDeniedError('The IsSubjectAdmin permission checker requires an assignmentid.')
        subjectid = self.view.args[0]
        _subjectadmin_required(user, subjectid)


class IsPeriodAdmin(BasePermission):
    """
    Djangorestframework permission checker that checks if the requesting user
    has admin-permissions on the period given as the first argument to the
    view.
    """
    def check_permission(self, user):
        if len(self.view.args) != 1:
            raise PermissionDeniedError('The IsPeriodAdmin permission checker requires an assignmentid.')
        periodid = self.view.args[0]
        periodadmin_required(user, periodid)


class IsAssignmentAdmin(BasePermission):
    """
    Djangorestframework permission checker that checks if the requesting user
    has admin-permissions on the assignment given as the first argument to the
    view.
    """
    def check_permission(self, user):
        if len(self.view.args) != 1:
            raise PermissionDeniedError('The IsAssignmentAdmin permission checker requires an assignmentid.')
        assignmentid = self.view.args[0]
        _assignmentadmin_required(user, assignmentid)
