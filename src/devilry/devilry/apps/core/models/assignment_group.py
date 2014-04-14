from datetime import datetime

from django.db.models import Q
from django.db import models
from django.db import transaction
from django.utils.translation import ugettext_lazy as _

from node import Node
from abstract_is_admin import AbstractIsAdmin
from abstract_is_examiner import AbstractIsExaminer
from assignment import Assignment
from model_utils import Etag
import deliverytypes
from .bulkcreateidentifier import BulkCreateIdentifier
from .bulkcreateidentifier import BulkCreateIdentifierField
from .bulkcreateidentifier import BulkCreateManagerMixin



class GroupPopValueError(ValueError):
    """
    Base class for exceptions raised by meth:`AssignmentGroup.pop_candidate`.
    """


class GroupPopToFewCandiatesError(GroupPopValueError):
    """
    Raised when meth:`AssignmentGroup.pop_candidate` is called on a group with
    1 or less candidates.
    """


class GroupPopNotCandiateError(GroupPopValueError):
    """
    Raised when meth:`AssignmentGroup.pop_candidate` is called with a candidate
    that is not on the group.
    """


class AssignmentGroupQuerySet(models.query.QuerySet):
    """
    The QuerySet used by :class:`.AssignmentGroupManager`.
    """
    def filter_is_examiner(self, user):
        return self.filter(examiners__user=user).distinct()

    def filter_is_candidate(self, user):
        return self.filter(candidates__student=user).distinct()

    def filter_is_published(self):
        return self.filter(parentnode__publishing_time__lt=datetime.now())

    def filter_is_active(self):
        now = datetime.now()
        return self.filter_is_published().filter(
            parentnode__parentnode__start_time__lt=now,
            parentnode__parentnode__end_time__gt=now)

    def filter_examiner_has_access(self, user):
        return self.filter_is_active().filter_is_examiner(user)

    def filter_student_has_access(self, user):
        return self.filter_is_published().filter_is_candidate(user)

    def filter_by_status(self, status):
        return self.filter(delivery_status=status)

    def filter_waiting_for_feedback(self):
        now = datetime.now()
        return self.filter(
            Q(parentnode__delivery_types=deliverytypes.NON_ELECTRONIC, delivery_status="waiting-for-something") |
            Q(parentnode__delivery_types=deliverytypes.ELECTRONIC, delivery_status="waiting-for-something", last_deadline__deadline__lte=now))

    def filter_waiting_for_deliveries(self):
        now = datetime.now()
        return self.filter(
            parentnode__delivery_types=deliverytypes.ELECTRONIC,
            delivery_status="waiting-for-something",
            last_deadline__deadline__gt=now)

    def close_groups(self):
        return self.update(
            is_open=False,
            delivery_status='closed-without-feedback'
        )

    def add_nonelectronic_delivery(self):
        for group in self.all():
            group.last_deadline.deliveries.create(
                delivery_type=deliverytypes.NON_ELECTRONIC,
                successful=True)

    def group_by_studentuser(self):
        """
        Group the AssignmentGroups by student. Showing this kind of grouping in
        the UI only makes sense when a student is candidate on multiple
        AssignmentGroups on the same assignment, but it is a useful utility when
        making other functions that require a map from the User object of a
        student to a group.

        :return:
            A dict where each key is a User object and each value is a list of
            groups where that user is :class:`.Candidate`.

        .. note::

            Not available on the :class:`.AssignmentGroupManager` because
            grouping like this is far to inefficient to ever use on all
            the AssignmentGroups.
        """
        groupsbystudentuser = {}
        for group in self.prefetch_related('candidates', 'candidates__student'):
            for candidate in group.candidates.all():
                if not candidate.student in groupsbystudentuser:
                    groupsbystudentuser[candidate.student] = []
                groupsbystudentuser[candidate.student].append(group)
        return groupsbystudentuser


    def group_by_examineruser(self):
        """
        Group the AssignmentGroups by examiner.

        :return:
            A dict where each key is a User object and each value is a list of
            groups where that user is :class:`.Examiner`.

        Example - group all groups on an assignment by examiner, and order groups by ::

            Examiner.objects\
                .filter(assignmentgroup__parentnode_id=1)\
                .order_by('user__username')\
                .groups_grouped_by_examiner()

        .. note::

            Not available on the :class:`.ExaminerManager` because
            grouping like this is far to inefficient to ever use on all
            the examiners in the database.
        """
        groupsbyexaminer = {}
        for group in self.prefetch_related('examiners', 'examiners__user'):
            for examiner in group.examiners.all():
                if not examiner.user in groupsbyexaminer:
                    groupsbyexaminer[examiner.user] = []
                groupsbyexaminer[examiner.user].append(group)
        return groupsbyexaminer


    def group_by_tags(self):
        """
        Group the AssignmentGroups in this queryset by their tags.

        Simple example::

            AssignmentGroup.objects.filter(parentnode=1).group_by_tags()

        You can order the AssignmentGroups before grouping them by tags, which
        will make each tag contain a list ordered like the queryset was
        ordered::

            AssignmentGroup.objects.filter(parentnode=1)\
                .order_by_candidate_full_name()\
                .group_by_tags()

        :return:
            A dict where each key is a tag (:obj:`.AssignmentGroupTag.tag`)
            and each value is a list of groups with that tag.

        .. note::

            Not available on the :class:`.AssignmentGroupManager` because
            grouping like this is far to inefficient to ever use on all
            the AssignmentGroups.
        """
        bytag = {}
        def add_to_tag(tag, group):
            if not tag in bytag:
                bytag[tag] = []
            bytag[tag].append(group)
        for group in self.prefetch_related('tags'):
            for tag in group.tags.all():
                add_to_tag(tag.tag, group)
        return bytag


    def order_by_candidate_full_name(self):
        """
        Order by the full name of the alphabetically first candidate in the 
        group.
        """
        return self.extra(
            select={
                'first_candidate_full_name': """
                    SELECT
                        core_devilryuserprofile.full_name as first_candidate_full_name
                    FROM core_candidate
                    INNER JOIN auth_user ON (auth_user.id = core_candidate.student_id)
                    INNER JOIN core_devilryuserprofile ON (core_devilryuserprofile.user_id = auth_user.id)
                    WHERE core_candidate.assignment_group_id = core_assignmentgroup.id
                    ORDER BY core_devilryuserprofile.full_name
                    LIMIT 0,1
                    """
            }
        ).order_by('first_candidate_full_name')

    def order_by_candidate_username(self):
        """
        Order by the username of the alphabetically first candidate in the 
        group.
        """
        return self.extra(
            select={
                'first_candidate_username': """
                    SELECT
                        auth_user.username as first_candidate_username
                    FROM core_candidate
                    INNER JOIN auth_user ON (auth_user.id = core_candidate.student_id)
                    WHERE core_candidate.assignment_group_id = core_assignmentgroup.id
                    ORDER BY auth_user.username
                    LIMIT 0,1
                    """
            }
        ).order_by('first_candidate_username')


    def order_by_examiner_full_name(self):
        """
        Order by the username of the alphabetically first examiner in the 
        group.
        """
        return self.extra(
            select={
                'first_examiner_full_name': """
                    SELECT
                        core_devilryuserprofile.full_name as first_examiner_full_name
                    FROM core_assignmentgroup_examiners
                    INNER JOIN auth_user ON (auth_user.id = core_assignmentgroup_examiners.user_id)
                    INNER JOIN core_devilryuserprofile ON (core_devilryuserprofile.user_id = auth_user.id)
                    WHERE core_assignmentgroup_examiners.assignmentgroup_id = core_assignmentgroup.id
                    ORDER BY core_devilryuserprofile.full_name
                    LIMIT 0,1
                    """
            }
        ).order_by('first_examiner_full_name')


    def order_by_examiner_username(self):
        """
        Order by the username of the alphabetically first examiner in the 
        group.
        """
        return self.extra(
            select={
                'first_examiner_username': """
                    SELECT
                        auth_user.username as first_examiner_username
                    FROM core_assignmentgroup_examiners
                    INNER JOIN auth_user ON (auth_user.id = core_assignmentgroup_examiners.user_id)
                    WHERE core_assignmentgroup_examiners.assignmentgroup_id = core_assignmentgroup.id
                    ORDER BY auth_user.username
                    LIMIT 0,1
                    """
            }
        ).order_by('first_examiner_username')


class AssignmentGroupManager(models.Manager, BulkCreateManagerMixin):
    """
    The Manager used by :class:`.AssignmentGroup`.
    """
    def get_queryset(self):
        return AssignmentGroupQuerySet(self.model, using=self._db)

    def filter(self, *args, **kwargs):
        return self.get_queryset().filter(*args, **kwargs)

    def all(self, *args, **kwargs):
        return self.get_queryset().all(*args, **kwargs)

    def order_by(self, *args, **kwargs):
        return self.get_queryset().order_by(*args, **kwargs)

    def filter_is_examiner(self, user):
        """
        Returns a queryset with all AssignmentGroups where the given ``user`` is examiner.

        WARNING: You should normally not use this directly because it gives the
        examiner information from expired periods (which they are not supposed
        to get). Use :meth:`.filter_examiner_has_access` instead.
        """
        return self.get_queryset().filter_is_examiner(user)

    def filter_is_candidate(self, user):
        """
        Returns a queryset with all AssignmentGroups where the given ``user`` is candidate.

        WARNING: You should normally not use this directly because it gives the
        student information from unpublished assignments (which they are not supposed
        to get). Use :meth:`.filter_student_has_access` instead.
        """
        return self.get_queryset().filter_is_candidate(user)

    def filter_is_published(self):
        """
        Returns a queryset with all AssignmentGroups on published Assignments.
        """
        return self.get_queryset().filter_is_published()

    def filter_is_active(self):
        """
        Returns a queryset with all AssignmentGroups on active Assignments.
        """
        return self.get_queryset().filter_is_active()

    def filter_examiner_has_access(self, user):
        """
        Returns a queryset with all AssignmentGroups on active Assignments
        where the given ``user`` is examiner.

        NOTE: This returns all groups that the given ``user`` has examiner-rights for.
        """
        return self.get_queryset().filter_examiner_has_access(user)

    def filter_student_has_access(self, user):
        """
        Returns a queryset with all AssignmentGroups on published Assignments
        where the given ``user`` is a candidate.

        NOTE: This returns all groups that the given ``user`` has student-rights for.
        """
        return self.get_queryset().filter_student_has_access(user)

    def filter_by_status(self, status):
        return self.get_queryset().filter_by_status(status)

    def filter_waiting_for_feedback(self):
        return self.get_queryset().filter_waiting_for_feedback()

    def filter_waiting_for_deliveries(self):
        return self.get_queryset().filter_waiting_for_deliveries()

    def close_groups(self):
        """
        Performs an efficient update of all the groups in the queryset
        setting ``is_open=False`` and ``delivery_status="closed-without-feedback"``.
        """
        return self.get_queryset().close_groups()

    def add_nonelectronic_delivery(self):
        """
        Add non-electronic delivery to all the groups in the queryset.

        Assumes that all the groups has ``last_deadline`` set.
        """
        return self.get_queryset().add_nonelectronic_delivery()

    def make_unique_bulkid(self):
        while True:
            bulkid = datetime.now()


    def create_x_groups(self, assignment, count):
        """
        Create ``count`` groups very efficiently.

        Perfect when you just want to create a set of groups on an assignment
        and fill them with data later. You will typically run this, followed
        by ``Candiate.objects.create_many(...)`` with the groups returned by this
        method as the first argument.

        Uses :class:`devilry.apps.core.models.BulkCreateIdentifier` to make it
        possible to efficiently create groups and get back the created groups.

        :param count: Number of groups to create.
        :return: The created groups.
        """
        bulkcreate_identifier = BulkCreateIdentifier.objects.create()
        def setup_group(x):
            return AssignmentGroup(
                parentnode=assignment,
                bulkcreate_identifier=bulkcreate_identifier)
        groups_to_create = map(setup_group, xrange(count))
        self.bulk_create(groups_to_create)
        return self.filter_by_bulkcreateidentifier(bulkcreate_identifier)

    def order_by_candidate_full_name(self):
        """
        Shortcut for ``AssignmentGroup.objects.get_queryset().order_by_candidate_full_name()``.
        See :meth:`.AssignmentGroupQuerySet.order_by_candidate_full_name`.
        """
        return self.get_queryset().order_by_candidate_full_name()

    def order_by_candidate_username(self):
        """
        Shortcut for ``AssignmentGroup.objects.get_queryset().order_by_candidate_username()``.
        See :meth:`.AssignmentGroupQuerySet.order_by_candidate_username`.
        """
        return self.get_queryset().order_by_candidate_username()

    def order_by_examiner_full_name(self):
        """
        Shortcut for ``AssignmentGroup.objects.get_queryset().order_by_examiner_full_name()``.
        See :meth:`.AssignmentGroupQuerySet.order_by_examiner_full_name`.
        """
        return self.get_queryset().order_by_examiner_full_name()

    def order_by_examiner_username(self):
        """
        Shortcut for ``AssignmentGroup.objects.get_queryset().order_by_examiner_username()``.
        See :meth:`.AssignmentGroupQuerySet.order_by_examiner_username`.
        """
        return self.get_queryset().order_by_examiner_username()


# TODO: Constraint: cannot be examiner and student on the same assignmentgroup as an option.
class AssignmentGroup(models.Model, AbstractIsAdmin, AbstractIsExaminer, Etag):
    """
    Represents a student or a group of students. 

    .. attribute:: parentnode

        A django.db.models.ForeignKey_ that points to the parent node,
        which is always an `Assignment`_.

    .. attribute:: name

        An optional name for the group.

    .. attribute:: candidates

        A django ``RelatedManager`` that holds the :class:`candidates <devilry.apps.core.models.Candidate>`
        on this group.

    .. attribute:: examiners

        A django.db.models.ManyToManyField_ that holds the examiner(s) that are
        to correct and grade the assignment.

    .. attribute:: is_open

        A django.db.models.BooleanField_ that tells you if the group can add
        deliveries or not.

    .. attribute:: deadlines

        A django ``RelatedManager`` that holds the :class:`deadlines <devilry.apps.core.models.Deadline>`
        on this group.

    .. attribute:: tags

        A django ``RelatedManager`` that holds the :class:`tags <devilry.apps.core.models.AssignmentGroupTag>`
        on this group.

    .. attribute:: feedback

       The last `StaticFeedback`_ (by save timestamp) on this assignmentgroup.

    .. attribute:: last_delivery

       The last :class:`devilry.apps.core.models.Delivery` on this assignmentgroup.

    .. attribute:: last_deadline

       The last :class:`devilry.apps.core.models.Deadline` for this assignmentgroup.

    .. attribute:: etag

       A DateTimeField containing the etag for this object.

    .. attribute:: delivery_status

       A CharField containing the status of the group.
       Valid status values:

           * "no-deadlines"
           * "corrected"
           * "closed-without-feedback"
           * "waiting-for-something"
    """

    objects = AssignmentGroupManager()

    parentnode = models.ForeignKey(Assignment, related_name='assignmentgroups')
    name = models.CharField(max_length=30, blank=True, null=True,
                           help_text='An optional name for the group. Typically used a project '\
                                       'name on project assignments.')
    is_open = models.BooleanField(blank=True, default=True,
            help_text = 'If this is checked, the group can add deliveries.')
    feedback = models.OneToOneField("StaticFeedback", blank=True, null=True)
    last_delivery = models.OneToOneField("Delivery", blank=True, null=True,
        related_name='last_delivery_by_group', on_delete=models.SET_NULL)
    last_deadline = models.OneToOneField("Deadline", blank=True, null=True,
        related_name='last_deadline_for_group', on_delete=models.SET_NULL)
    etag = models.DateTimeField(auto_now_add=True)
    delivery_status = models.CharField(max_length=30, blank=True, null=True,
        help_text='The delivery_status of a group',
        choices=(
            ("no-deadlines", _("No deadlines")),
            ("corrected", _("Corrected")),
            ("closed-without-feedback", _("Closed without feedback")),
            ("waiting-for-something", _("Waiting for something")),
        ))
    bulkcreate_identifier = BulkCreateIdentifierField()


    class Meta:
        app_label = 'core'
        ordering = ['id']

    def save(self, *args, **kwargs):
        """
        :param update_delivery_status:
            Update the ``delivery_status``? This is a somewhat expensive
            operation, so we provide the option to avoid it if needed.
            Defaults to ``True``.
        :param autocreate_first_deadline_for_nonelectronic:
            Autocreate the first deadline if non-electronic assignment?
            Defaults to ``True``.
        """
        autocreate_first_deadline_for_nonelectronic = kwargs.pop('autocreate_first_deadline_for_nonelectronic', True)
        create_dummy_deadline = False
        if autocreate_first_deadline_for_nonelectronic \
                and self.id is None \
                and self.parentnode.delivery_types == deliverytypes.NON_ELECTRONIC:
            create_dummy_deadline = True
        if kwargs.pop('update_delivery_status', True):
            self._set_delivery_status()
        super(AssignmentGroup, self).save(*args, **kwargs)
        if create_dummy_deadline:
            self.deadlines.create(deadline=self.parentnode.parentnode.end_time)

    @classmethod
    def q_is_admin(cls, user_obj):
        return Q(parentnode__admins=user_obj) | \
                Q(parentnode__parentnode__admins=user_obj) | \
                Q(parentnode__parentnode__parentnode__admins=user_obj) | \
                Q(parentnode__parentnode__parentnode__parentnode__pk__in=Node._get_nodepks_where_isadmin(user_obj))

    @classmethod
    def q_is_candidate(cls, user_obj):
        """
        Returns a django.models.Q object matching AssignmentGroups where
        the given student is candidate.
        """
        return Q(candidates__student=user_obj)

    @classmethod
    def where_is_candidate(cls, user_obj):
        """ Returns a QuerySet matching all AssignmentGroups where the
        given user is student.

        :param user_obj: A django.contrib.auth.models.User_ object.
        :rtype: QuerySet
        """
        return AssignmentGroup.objects.filter(cls.q_is_candidate(user_obj))

    @classmethod
    def published_where_is_candidate(cls, user_obj, old=True, active=True):
        """ Returns a QuerySet matching all :ref:`published
        <assignment-classifications>` assignment groups where the given user
        is student.

        :param user_obj: A django.contrib.auth.models.User_ object.
        :rtype: QuerySet
        """
        return AssignmentGroup.objects.filter(
                cls.q_is_candidate(user_obj) &
                cls.q_published(old=old, active=active))

    @classmethod
    def active_where_is_candidate(cls, user_obj):
        """ Returns a QuerySet matching all :ref:`active
        <assignment-classifications>` assignment groups where the given user
        is student.

        :param user_obj: A django.contrib.auth.models.User_ object.
        :rtype: QuerySet
        """
        return cls.published_where_is_candidate(user_obj, old=False)

    @classmethod
    def old_where_is_candidate(cls, user_obj):
        """ Returns a QuerySet matching all :ref:`old
        <assignment-classifications>` assignment groups where the given user
        is student.

        :param user_obj: A django.contrib.auth.models.User_ object.
        :rtype: QuerySet
        """
        return cls.published_where_is_candidate(user_obj, active=False)

    @classmethod
    def q_published(cls, old=True, active=True):
        now = datetime.now()
        q = Q(parentnode__publishing_time__lt = now)
        if not active:
            q &= ~Q(parentnode__parentnode__end_time__gte = now)
        if not old:
            q &= ~Q(parentnode__parentnode__end_time__lt = now)
        return q

    @classmethod
    def q_is_examiner(cls, user_obj):
        return Q(examiners__user=user_obj)


    @property
    def should_ask_if_examiner_want_to_give_another_chance(self):
        """
        ``True`` if the current state of the group is such that the examiner should
        be asked if they want to give them another chance.
        
        ``True`` if corrected with failing grade or closed without feedback.
        """
        if self.assignment.is_electronic:
            return (self.delivery_status == "corrected" and not self.feedback.is_passing_grade) \
                or self.delivery_status == 'closed-without-feedback'
        else:
            return False

    @property
    def missing_expected_delivery(self):
        """
        Return ``True`` if the group has no deliveries, and we are expecting
        them to have made at least one delivery on the last deadline.
        """
        if self.assignment.is_electronic and self.get_status() == "waiting-for-feedback":
            if not self.last_delivery:
                return True
            elif self.last_deadline and self.last_delivery.deadline != self.last_deadline:
                return True
        return False

    @property
    def subject(self):
        """
        Shortcut for ``parentnode.parentnode.parentnode``.
        """
        return self.parentnode.parentnode.parentnode

    @property
    def period(self):
        """
        Shortcut for ``parentnode.parentnode``.
        """
        return self.parentnode.parentnode

    @property
    def assignment(self):
        """
        Alias for :obj:`.parentnode`.
        """
        return self.parentnode

    def get_candidate_ids(self, nonevalue='unknown-candidateid'):
        """
        Get the candidate ids of all Candidates on this group.
        Should only be used with anonymous groups.
        """
        return [candidate.candidate_id or nonevalue for candidate in self.candidates.all()]


    @property
    def short_displayname(self):
        """
        A short displayname for the group. If the assignment is anonymous,
        we list the candidate IDs. If the group has a name, the name is used,
        else we fall back to a comma separated list of usernames. If the group has no name and no
        students, we use the ID.

        .. seealso:: https://github.com/devilry/devilry-django/issues/498
        """
        if self.assignment.anonymous:
            out = ', '.join(self.get_candidate_ids())
        elif self.name:
            out = self.name
        else:
            out = self.get_students()
        if out == '':
            return unicode(self.id)
        else:
            return out

    @property
    def long_displayname(self):
        """
        A long displayname for the group. If the assignment is anonymous,
        we list the candidate IDs.

        If the assignment is not anonymous, we use a comma separated list of
        the displaynames (full names with fallback to username) of the
        students. If the group has a name, we use the groupname with the names
        of the students in parenthesis.

        .. seealso:: https://github.com/devilry/devilry-django/issues/499
        """
        if self.assignment.anonymous:
            out = ', '.join(self.get_candidate_ids())
        else:
            candidates = self.candidates.select_related('student', 'student__devilryuserprofile')
            names = [candidate.student.devilryuserprofile.get_displayname() for candidate in candidates]
            out = u', '.join(names)
            if self.name:
                out = u'{} ({})'.format(self.name, out)
        if out == '':
            return unicode(self.id)
        else:
            return out

    def __unicode__(self):
        return u'AssignmentGroup(id={id})'.format(id=self.id)

    def get_students(self, separator=u', '):
        """ Get a string containing all students in the group separated by
        comma and a space, like: ``superman, spiderman, batman``.

        **WARNING:** You should never use this method when the user is not
        an administrator. Use :meth:`get_candidates`
        instead.
        """
        candidates = self.candidates.select_related('student').order_by('student__username')
        return separator.join([c.student.username for c in candidates])

    def get_candidates(self, separator=u', '):
        """
        Get a string containing all candiates in the group separated by
        comma and a space, like: ``superman, spiderman, batman`` for normal
        assignments, and something like: ``321, 1533, 111`` for anonymous
        assignments.

        :param separator: The unicode string used to separate candidates. Defaults to ``u', '``.
        """
        if self.parentnode.anonymous:
            return separator.join(self.get_candidate_ids())
        else:
            return self.get_students(separator)

    def get_examiners(self, separator=u', '):
        """
        Get a string contaning the username of all examiners in the group separated by
        comma (``','``).

        :param separator: The unicode string used to separate candidates. Defaults to ``u', '``.
        """
        return separator.join([examiner.user.username for examiner in self.examiners.select_related('user')])

    def is_admin(self, user_obj):
        return self.parentnode.is_admin(user_obj)

    def is_candidate(self, user_obj):
        return self.candidates.filter(student=user_obj).count() > 0

    def is_examiner(self, user_obj):
        """ Return True if user is examiner on this assignment group """
        return self.examiners.filter(user__id=user_obj.pk).count() > 0

    def can_delete(self, user_obj):
        """
        Check if the given user is permitted to delete this AssignmentGroup. A user is
        permitted to delete an object if the user is superadmin, or if the user
        is admin on the assignment (uses :meth:`.is_admin`). Only superusers
        are allowed to delete AssignmentGroups where :meth:`.is_empty` returns ``False``.

        .. note::
            This method can also be used to check if candidates can be
            removed from the group.

        :return: ``True`` if the user is permitted to delete this object.
        """
        if self.id == None:
            return False
        if user_obj.is_superuser:
            return True
        if self.parentnode != None and self.is_empty():
            return self.parentnode.is_admin(user_obj)
        else:
            return False

    def is_empty(self):
        """
        Returns ``True`` if this AssignmentGroup does not contain any deliveries.
        """
        from .delivery import Delivery
        return Delivery.objects.filter(deadline__assignment_group=self).count() == 0

    def get_active_deadline(self):
        """ Get the active :class:`Deadline`.

        This is always the last deadline on this group.

        :return:
            The latest deadline.
        """
        return self.deadlines.all().order_by('-deadline')[0]

    def can_save(self, user_obj):
        """ Check if the user has permission to save this AssignmentGroup. """
        if user_obj.is_superuser:
            return True
        elif self.parentnode:
            return self.parentnode.is_admin(user_obj)
        else:
            return False

    def can_add_deliveries(self):
        """ Returns true if a student can add deliveries on this assignmentgroup

        Both the assignmentgroups is_open attribute, and the periods start
        and end time is checked.
        """
        return self.is_open and self.parentnode.parentnode.is_active()

    def copy_all_except_candidates(self):
        """
        .. note:: Always run this is a transaction.
        """
        groupcopy = AssignmentGroup(parentnode=self.parentnode,
                                    name=self.name,
                                    is_open=self.is_open,
                                    delivery_status=self.delivery_status)
        groupcopy.full_clean()
        groupcopy.save(update_delivery_status=False)
        for tagobj in self.tags.all():
            groupcopy.tags.create(tag=tagobj.tag)
        for examiner in self.examiners.all():
            groupcopy.examiners.create(user=examiner.user)
        for deadline in self.deadlines.all():
            deadline.copy(groupcopy)
        groupcopy._set_latest_feedback_as_active()
        groupcopy._set_last_delivery()
        groupcopy.save(update_delivery_status=False)
        return groupcopy

    def pop_candidate(self, candidate):
        """
        Make a copy of this group using ``copy_all_except_candidates``, and
        add given candidate to the copied group and remove the candidate from
        this group.

        :param candidate: A :class:`devilry.apps.core.models.Candidate` object. The candidate must be among the candidates on this group.

        .. note:: Always run this is a transaction.
        """
        candidates = self.candidates.all()
        if len(candidates) < 2:
            raise GroupPopToFewCandiatesError('Can not pop candidates on a group with less than 2 candidates.')
        if not candidate in candidates:
            raise GroupPopNotCandiateError('The candidate to pop must be in the original group.')

        assignment = self.parentnode
        groupcopy = self.copy_all_except_candidates()
        candidate.assignment_group = groupcopy # Move the candidate to the new group
        candidate.full_clean()
        candidate.save()
        return groupcopy

    def recalculate_delivery_numbers(self):
        """
        Query all ``successful`` deliveries on this AssignmentGroup, ordered by
        ``time_of_delivery`` ascending, and number them with the oldest delivery
        as number 1.
        """
        from .delivery import Delivery
        qry = Delivery.objects.filter(deadline__assignment_group=self,
                                      successful=True)
        qry = qry.order_by('time_of_delivery')
        for number, delivery in enumerate(qry, 1):
            delivery.number = number
            delivery.save(autoset_number=False,
                          autoset_last_delivery_on_group=False,
                          autoset_time_of_delivery=False)


    @property
    def successful_delivery_count(self):
        from .delivery import Delivery
        return Delivery.objects.filter(
            successful=True,
            deadline__assignment_group=self).count()
    

    def _set_delivery_status(self):
        """
        Set the ``delivery_status``. Calculated with this algorithm:

        - If open:
            - If no deadlines
                - ``no-deadlines``
            - Else:
                - ``waiting-for-something``
        - If closed:
            - If feedback:
                - ``corrected``
            - If not:
                - ``closed-without-feedback``

        .. warning:: Only sets ``delivery_status``, does not save.

        :return:
            One of ``waiting-for-deliveries``, ``waiting-for-feedback``,
            ``no-deadlines``, ``corrected`` or ``closed-without-feedback``.
        """
        if self.is_open:
            if self.deadlines.exists():
                self.delivery_status = 'waiting-for-something'
            else:
                self.delivery_status = 'no-deadlines'
        else:
            if self.feedback:
                self.delivery_status = 'corrected'
            else:
                self.delivery_status = 'closed-without-feedback'

    def _merge_examiners_into(self, target):
        target_examiners = set([e.user.id for e in target.examiners.all()])
        for examiner in self.examiners.all():
            if not examiner.user.id in target_examiners:
                examiner.assignmentgroup = target
                examiner.save()

    def _merge_candidates_into(self, target):
        self.candidates\
            .exclude(student__in=target.candidates.values_list('student', flat=True))\
            .update(assignment_group=target)

    def _set_latest_feedback_as_active(self):
        from .static_feedback import StaticFeedback
        feedbacks = StaticFeedback.objects.order_by('-save_timestamp').filter(delivery__deadline__assignment_group=self)[:1]
        self.feedback = None  # NOTE: Required to avoid IntegrityError caused by non-unique feedback_id
        if len(feedbacks) == 1:
            latest_feedback = feedbacks[0]
            self.feedback = latest_feedback

    def _set_last_delivery(self):
        from .delivery import Delivery
        try:
            last_delivery = Delivery.objects.filter(
                successful=True,
                deadline__assignment_group=self).order_by('-time_of_delivery')[0]
        except IndexError:
            self.last_delivery = None
        else:
            self.last_delivery = last_delivery

    def merge_into(self, target):
        """
        Merge this AssignmentGroup into the ``target`` AssignmentGroup.
        Algorithm:

            - Copy in all candidates and examiners not already on the
              AssignmentGroup.
            - Delete all copies where the original is in ``self`` or ``target``:
                - Delete all deliveries from ``target`` that are ``copy_of`` a delivery
                  ``self``.
                - Delete all deliveries from ``self`` that are ``copy_of`` a delivery in
                  ``target``.
            - Loop through all deadlines in this AssignmentGroup, and for each
              deadline:

              If the datetime and text of the deadline matches one already in
              ``target``, move the remaining deliveries into the target deadline.

              If the deadline and text does NOT match a deadline already in
              ``target``, change assignmentgroup of the deadline to the
              master group.
            - Recalculate delivery numbers of ``target`` using
              :meth:`recalculate_delivery_numbers`.
            - Run ``self.delete()``.
            - Set the latest feedback on ``target`` as the active feedback.

        .. note::
            The ``target.name`` or ``target.is_open`` is not changed.

        .. note::
            Everything except setting the latest feedback runs in a
            transaction. Setting the latest feedback does not run
            in transaction because we need to save the with ``feedback=None``,
            and then set the *new* latest feedback to avoid IntegrityError.
        """
        from .deadline import Deadline
        from .delivery import Delivery
        with transaction.commit_on_success():
            # Unset last_deadline - if we not do this, we will get
            # ``IntegrityError: column last_deadline_id is not unique``
            # if the last deadline after the merge is self.last_deadline
            self.last_deadline = None
            self.save(update_delivery_status=False)

            # Copies
            Delivery.objects.filter(deadline__assignment_group=self,
                                    copy_of__deadline__assignment_group=target).delete()
            Delivery.objects.filter(deadline__assignment_group=target,
                                    copy_of__deadline__assignment_group=self).delete()

            # Examiners and candidates
            self._merge_examiners_into(target)
            self._merge_candidates_into(target)

            # Deadlines
            for deadline in self.deadlines.all():
                try:
                    matching_deadline = target.deadlines.get(deadline=deadline.deadline,
                                                             text=deadline.text)
                    for delivery in deadline.deliveries.all():
                        if delivery.copy_of:
                            # NOTE: If we merge 2 groups with a copy from the same third group, we
                            #       we only want one of the copies.
                            if Delivery.objects.filter(deadline__assignment_group=target,
                                                       copy_of=delivery.copy_of).exists():
                                continue
                        delivery.deadline = matching_deadline
                        delivery.save(autoset_time_of_delivery=False,
                                      autoset_last_delivery_on_group=False,
                                      autoset_number=False)
                except Deadline.DoesNotExist:
                    deadline.assignment_group = target
                    deadline.save()
            target.recalculate_delivery_numbers()
            self.delete()
        target._set_latest_feedback_as_active()
        target._set_last_delivery()
        target.save()

    @classmethod
    def merge_many_groups(self, sources, target):
        """
        Loop through the ``sources``-iterable, and for each ``source`` in the
        iterator, run ``source.merge_into(target)``.
        """
        for source in sources:
            source.merge_into(target) # Source is deleted after this

    def get_status(self):
        """
        Get the status of the group. Calculated with this algorithm::

            if ``delivery_status == 'waiting-for-something'``
                if assignment.delivery_types==NON_ELECTRONIC:
                    "waiting-for-feedback"
                else
                    if before deadline
                        "waiting-for-deliveries"
                    if after deadline:
                        "waiting-for-feedback"
            else
                delivery_status
        """
        if self.delivery_status == 'waiting-for-something':
            if self.assignment.delivery_types == deliverytypes.NON_ELECTRONIC:
                return 'waiting-for-feedback'
            else:
                now = datetime.now()
                if self.last_deadline.deadline > now:
                    return 'waiting-for-deliveries'
                else:
                    return 'waiting-for-feedback'
        else:
            return self.delivery_status

    def get_all_admin_ids(self):
        return self.parentnode.get_all_admin_ids()


class AssignmentGroupTag(models.Model):
    """
    An AssignmentGroup can be tagged with zero or more tags using this class.
    """
    #: The `AssignmentGroup`_ where this groups belongs.
    assignment_group = models.ForeignKey(AssignmentGroup, related_name='tags')

    #: The tag. Max 20 characters. Can only contain a-z, A-Z, 0-9 and "_".
    tag = models.SlugField(max_length=20, help_text='A tag can contain a-z, A-Z, 0-9 and "_".')

    class Meta:
        app_label = 'core'
        ordering = ['tag']
        unique_together = ('assignment_group', 'tag')

    def __unicode__(self):
        return self.tag
