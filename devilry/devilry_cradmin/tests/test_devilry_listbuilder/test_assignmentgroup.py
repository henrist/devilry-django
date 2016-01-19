from datetime import timedelta

import htmls
from django import test
from django.utils import timezone
from model_mommy import mommy

from devilry.apps.core.models import Assignment, AssignmentGroup
from devilry.devilry_cradmin import devilry_listbuilder
from devilry.devilry_group import devilry_group_mommy_factories


class TestFullyAnonymousSubjectAdminItemValue(test.TestCase):
    def test_non_anonymous_not_allowed(self):
        testgroup = mommy.make('core.AssignmentGroup')
        with self.assertRaisesMessage(ValueError,
                                      'Can only use FullyAnonymousSubjectAdminItemValue for fully '
                                      'anonymous assignments. Use SubjectAdminItemValue istead.'):
            devilry_listbuilder.assignmentgroup.FullyAnonymousSubjectAdminItemValue(value=testgroup)

    def test_semi_anonymous_is_not_allowed(self):
        testgroup = mommy.make('core.AssignmentGroup',
                               parentnode__anonymizationmode=Assignment.ANONYMIZATIONMODE_SEMI_ANONYMOUS)
        with self.assertRaisesMessage(ValueError,
                                      'Can only use FullyAnonymousSubjectAdminItemValue for fully '
                                      'anonymous assignments. Use SubjectAdminItemValue istead.'):
            devilry_listbuilder.assignmentgroup.FullyAnonymousSubjectAdminItemValue(value=testgroup)

    def test_name_fully_anonymous_is_not_anoymized(self):
        testgroup = mommy.make('core.AssignmentGroup',
                               parentnode__anonymizationmode=Assignment.ANONYMIZATIONMODE_FULLY_ANONYMOUS)
        mommy.make('core.Candidate',
                   assignment_group=testgroup,
                   relatedstudent__user__fullname='Test User',
                   relatedstudent__user__shortname='testuser@example.com')
        selector = htmls.S(devilry_listbuilder.assignmentgroup.FullyAnonymousSubjectAdminItemValue(
            value=testgroup).render())
        self.assertEqual(
            'Test User(testuser@example.com)',
            selector.one('.django-cradmin-listbuilder-itemvalue-titledescription-title').alltext_normalized)


class TestStudentItemValue(test.TestCase):
    def test_name(self):
        testgroup = mommy.make('core.AssignmentGroup')
        mommy.make('core.Candidate',
                   assignment_group=testgroup,
                   relatedstudent__user__fullname='Test User',
                   relatedstudent__user__shortname='testuser@example.com')
        selector = htmls.S(devilry_listbuilder.assignmentgroup.StudentItemValue(
            value=testgroup, assignment=testgroup.assignment).render())
        self.assertEqual(
            'Test User(testuser@example.com)',
            selector.one('.django-cradmin-listbuilder-itemvalue-titledescription-title').alltext_normalized)

    def test_name_semi_anonymous_is_not_anoymized(self):
        testgroup = mommy.make('core.AssignmentGroup',
                               parentnode__anonymizationmode=Assignment.ANONYMIZATIONMODE_SEMI_ANONYMOUS)
        mommy.make('core.Candidate',
                   assignment_group=testgroup,
                   relatedstudent__user__fullname='Test User',
                   relatedstudent__user__shortname='testuser@example.com')
        selector = htmls.S(devilry_listbuilder.assignmentgroup.StudentItemValue(
            value=testgroup, assignment=testgroup.assignment).render())
        self.assertEqual(
            'Test User(testuser@example.com)',
            selector.one('.django-cradmin-listbuilder-itemvalue-titledescription-title').alltext_normalized)

    def test_name_fully_anonymous_is_not_anoymized(self):
        testgroup = mommy.make('core.AssignmentGroup',
                               parentnode__anonymizationmode=Assignment.ANONYMIZATIONMODE_FULLY_ANONYMOUS)
        mommy.make('core.Candidate',
                   assignment_group=testgroup,
                   relatedstudent__user__fullname='Test User',
                   relatedstudent__user__shortname='testuser@example.com')
        selector = htmls.S(devilry_listbuilder.assignmentgroup.StudentItemValue(
            value=testgroup, assignment=testgroup.assignment).render())
        self.assertEqual(
            'Test User(testuser@example.com)',
            selector.one('.django-cradmin-listbuilder-itemvalue-titledescription-title').alltext_normalized)

    def test_examiners(self):
        testgroup = mommy.make('core.AssignmentGroup')
        mommy.make('core.Examiner',
                   assignmentgroup=testgroup,
                   relatedexaminer__user__fullname='Test User',
                   relatedexaminer__user__shortname='testuser@example.com')
        selector = htmls.S(devilry_listbuilder.assignmentgroup.StudentItemValue(
            value=testgroup, assignment=testgroup.assignment).render())
        self.assertEqual(
            'Test User(testuser@example.com)',
            selector.one('.devilry-cradmin-groupitemvalue-examiners-names').alltext_normalized)

    def test_examiners_semi_anonymous(self):
        testgroup = mommy.make('core.AssignmentGroup',
                               parentnode__anonymizationmode=Assignment.ANONYMIZATIONMODE_SEMI_ANONYMOUS)
        mommy.make('core.Examiner',
                   assignmentgroup=testgroup,
                   relatedexaminer__automatic_anonymous_id='MyAnonymousID')
        selector = htmls.S(devilry_listbuilder.assignmentgroup.StudentItemValue(
            value=testgroup, assignment=testgroup.assignment).render())
        self.assertEqual(
            'MyAnonymousID',
            selector.one('.devilry-cradmin-groupitemvalue-examiners-names').alltext_normalized)

    def test_examiners_fully_anonymous(self):
        testgroup = mommy.make('core.AssignmentGroup',
                               parentnode__anonymizationmode=Assignment.ANONYMIZATIONMODE_FULLY_ANONYMOUS)
        mommy.make('core.Examiner',
                   assignmentgroup=testgroup,
                   relatedexaminer__automatic_anonymous_id='MyAnonymousID')
        selector = htmls.S(devilry_listbuilder.assignmentgroup.StudentItemValue(
            value=testgroup, assignment=testgroup.assignment).render())
        self.assertEqual(
            'MyAnonymousID',
            selector.one('.devilry-cradmin-groupitemvalue-examiners-names').alltext_normalized)

    def test_grade_students_can_see_points_false(self):
        devilry_group_mommy_factories.feedbackset_first_try_published(
            group__parentnode__students_can_see_points=False,
            grading_points=1)
        testgroup = AssignmentGroup.objects\
            .annotate_with_is_corrected()\
            .annotate_with_grading_points()\
            .first()
        selector = htmls.S(devilry_listbuilder.assignmentgroup.StudentItemValue(
            value=testgroup, assignment=testgroup.assignment).render())
        self.assertEqual(
            'Grade: passed',
            selector.one('.devilry-cradmin-groupitemvalue-grade').alltext_normalized)

    def test_grade_students_can_see_points_true(self):
        devilry_group_mommy_factories.feedbackset_first_try_published(
            group__parentnode__students_can_see_points=True,
            grading_points=1)
        testgroup = AssignmentGroup.objects\
            .annotate_with_is_corrected()\
            .annotate_with_grading_points()\
            .first()
        selector = htmls.S(devilry_listbuilder.assignmentgroup.StudentItemValue(
            value=testgroup, assignment=testgroup.assignment).render())
        self.assertEqual(
            'Grade: passed (1/1)',
            selector.one('.devilry-cradmin-groupitemvalue-grade').alltext_normalized)


class TestExaminerItemValue(test.TestCase):
    def test_name(self):
        testgroup = mommy.make('core.AssignmentGroup')
        mommy.make('core.Candidate',
                   assignment_group=testgroup,
                   relatedstudent__user__fullname='Test User',
                   relatedstudent__user__shortname='testuser@example.com')
        selector = htmls.S(devilry_listbuilder.assignmentgroup.ExaminerItemValue(
            value=testgroup, assignment=testgroup.assignment).render())
        self.assertEqual(
            'Test User(testuser@example.com)',
            selector.one('.django-cradmin-listbuilder-itemvalue-titledescription-title').alltext_normalized)

    def test_name_semi_anonymous_is_anonymized(self):
        testgroup = mommy.make('core.AssignmentGroup',
                               parentnode__anonymizationmode=Assignment.ANONYMIZATIONMODE_SEMI_ANONYMOUS)
        mommy.make('core.Candidate',
                   assignment_group=testgroup,
                   relatedstudent__automatic_anonymous_id='MyAnonymousID')
        selector = htmls.S(devilry_listbuilder.assignmentgroup.ExaminerItemValue(
            value=testgroup, assignment=testgroup.assignment).render())
        self.assertEqual(
            'MyAnonymousID',
            selector.one('.django-cradmin-listbuilder-itemvalue-titledescription-title').alltext_normalized)

    def test_name_fully_anonymous_is_anonymized(self):
        testgroup = mommy.make('core.AssignmentGroup',
                               parentnode__anonymizationmode=Assignment.ANONYMIZATIONMODE_FULLY_ANONYMOUS)
        mommy.make('core.Candidate',
                   assignment_group=testgroup,
                   relatedstudent__automatic_anonymous_id='MyAnonymousID')
        selector = htmls.S(devilry_listbuilder.assignmentgroup.ExaminerItemValue(
            value=testgroup, assignment=testgroup.assignment).render())
        self.assertEqual(
            'MyAnonymousID',
            selector.one('.django-cradmin-listbuilder-itemvalue-titledescription-title').alltext_normalized)

    def test_examiners_include_examiners_false(self):
        testgroup = mommy.make('core.AssignmentGroup')
        mommy.make('core.Examiner',
                   assignmentgroup=testgroup,
                   relatedexaminer__user__fullname='Test User',
                   relatedexaminer__user__shortname='testuser@example.com')
        selector = htmls.S(devilry_listbuilder.assignmentgroup.ExaminerItemValue(
            value=testgroup, assignment=testgroup.assignment, include_examiners=False).render())
        self.assertFalse(selector.exists('.devilry-cradmin-groupitemvalue-examiners-names'))
        self.assertFalse(selector.exists('.devilry-cradmin-groupitemvalue-examiners'))

    def test_examiners_include_examiners_true(self):
        testgroup = mommy.make('core.AssignmentGroup')
        mommy.make('core.Examiner',
                   assignmentgroup=testgroup,
                   relatedexaminer__user__fullname='Test User',
                   relatedexaminer__user__shortname='testuser@example.com')
        selector = htmls.S(devilry_listbuilder.assignmentgroup.ExaminerItemValue(
            value=testgroup, assignment=testgroup.assignment, include_examiners=True).render())
        self.assertEqual(
            'Test User(testuser@example.com)',
            selector.one('.devilry-cradmin-groupitemvalue-examiners-names').alltext_normalized)

    def test_examiners_semi_anonymous_include_examiners_true(self):
        testgroup = mommy.make('core.AssignmentGroup',
                               parentnode__anonymizationmode=Assignment.ANONYMIZATIONMODE_SEMI_ANONYMOUS)
        mommy.make('core.Examiner',
                   assignmentgroup=testgroup,
                   relatedexaminer__user__fullname='Test User',
                   relatedexaminer__user__shortname='testuser@example.com')
        selector = htmls.S(devilry_listbuilder.assignmentgroup.ExaminerItemValue(
            value=testgroup, assignment=testgroup.assignment, include_examiners=True).render())
        self.assertEqual(
            'Test User(testuser@example.com)',
            selector.one('.devilry-cradmin-groupitemvalue-examiners-names').alltext_normalized)

    def test_examiners_fully_anonymous_include_examiners_true(self):
        testgroup = mommy.make('core.AssignmentGroup',
                               parentnode__anonymizationmode=Assignment.ANONYMIZATIONMODE_FULLY_ANONYMOUS)
        mommy.make('core.Examiner',
                   assignmentgroup=testgroup,
                   relatedexaminer__user__fullname='Test User',
                   relatedexaminer__user__shortname='testuser@example.com')
        selector = htmls.S(devilry_listbuilder.assignmentgroup.ExaminerItemValue(
            value=testgroup, assignment=testgroup.assignment, include_examiners=True).render())
        self.assertEqual(
            'Test User(testuser@example.com)',
            selector.one('.devilry-cradmin-groupitemvalue-examiners-names').alltext_normalized)

    def test_has_unpublished_feedbackdraft_draft_false(self):
        devilry_group_mommy_factories.feedbackset_first_try_published(grading_points=1),
        testgroup = AssignmentGroup.objects.annotate_with_has_unpublished_feedbackdraft().first()
        selector = htmls.S(devilry_listbuilder.assignmentgroup.ExaminerItemValue(
            value=testgroup, assignment=testgroup.assignment).render())
        self.assertFalse(selector.exists('.devilry-cradmin-groupitemvalue-unpublished-feedbackdraft'))

    def test_has_unpublished_feedbackdraft_draft_true(self):
        devilry_group_mommy_factories.feedbackset_first_try_unpublished(grading_points=1),
        testgroup = AssignmentGroup.objects.annotate_with_has_unpublished_feedbackdraft().first()
        selector = htmls.S(devilry_listbuilder.assignmentgroup.ExaminerItemValue(
            value=testgroup, assignment=testgroup.assignment).render())
        self.assertEqual(
            'Unpublished feedback draft',
            selector.one('.devilry-cradmin-groupitemvalue-unpublished-feedbackdraft').alltext_normalized)

    def test_grade_students_can_see_points_false(self):
        devilry_group_mommy_factories.feedbackset_first_try_published(
            group__parentnode__students_can_see_points=False,
            grading_points=1)
        testgroup = AssignmentGroup.objects\
            .annotate_with_is_corrected()\
            .annotate_with_grading_points()\
            .first()
        selector = htmls.S(devilry_listbuilder.assignmentgroup.ExaminerItemValue(
            value=testgroup, assignment=testgroup.assignment).render())
        self.assertEqual(
            'Grade: passed (1/1)',
            selector.one('.devilry-cradmin-groupitemvalue-grade').alltext_normalized)

    def test_grade_students_can_see_points_true(self):
        devilry_group_mommy_factories.feedbackset_first_try_published(
            group__parentnode__students_can_see_points=True,
            grading_points=1)
        testgroup = AssignmentGroup.objects\
            .annotate_with_is_corrected()\
            .annotate_with_grading_points()\
            .first()
        selector = htmls.S(devilry_listbuilder.assignmentgroup.ExaminerItemValue(
            value=testgroup, assignment=testgroup.assignment).render())
        self.assertEqual(
            'Grade: passed (1/1)',
            selector.one('.devilry-cradmin-groupitemvalue-grade').alltext_normalized)


class TestPeriodAdminItemValue(test.TestCase):
    def test_name(self):
        testgroup = mommy.make('core.AssignmentGroup')
        mommy.make('core.Candidate',
                   assignment_group=testgroup,
                   relatedstudent__user__fullname='Test User',
                   relatedstudent__user__shortname='testuser@example.com')
        selector = htmls.S(devilry_listbuilder.assignmentgroup.PeriodAdminItemValue(
            value=testgroup, assignment=testgroup.assignment).render())
        self.assertEqual(
            'Test User(testuser@example.com)',
            selector.one('.django-cradmin-listbuilder-itemvalue-titledescription-title').alltext_normalized)

    def test_anonymous_not_allowed(self):
        testgroup = mommy.make('core.AssignmentGroup',
                               parentnode__anonymizationmode=Assignment.ANONYMIZATIONMODE_SEMI_ANONYMOUS)
        with self.assertRaisesMessage(ValueError,
                                      'Can not use PeriodAdminItemValue for anonymous assignments. '
                                      'Periodadmins are not supposed have access to them.'):
            devilry_listbuilder.assignmentgroup.PeriodAdminItemValue(value=testgroup, assignment=testgroup.assignment)

    def test_examiners(self):
        testgroup = mommy.make('core.AssignmentGroup')
        mommy.make('core.Examiner',
                   assignmentgroup=testgroup,
                   relatedexaminer__user__fullname='Test User',
                   relatedexaminer__user__shortname='testuser@example.com')
        selector = htmls.S(devilry_listbuilder.assignmentgroup.PeriodAdminItemValue(
            value=testgroup, assignment=testgroup.assignment).render())
        self.assertEqual(
            'Test User(testuser@example.com)',
            selector.one('.devilry-cradmin-groupitemvalue-examiners-names').alltext_normalized)

    def test_grade_students_can_see_points_false(self):
        devilry_group_mommy_factories.feedbackset_first_try_published(
            group__parentnode__students_can_see_points=False,
            grading_points=1)
        testgroup = AssignmentGroup.objects\
            .annotate_with_is_corrected()\
            .annotate_with_grading_points()\
            .first()
        selector = htmls.S(devilry_listbuilder.assignmentgroup.PeriodAdminItemValue(
            value=testgroup, assignment=testgroup.assignment).render())
        self.assertEqual(
            'Grade: passed (1/1)',
            selector.one('.devilry-cradmin-groupitemvalue-grade').alltext_normalized)

    def test_grade_students_can_see_points_true(self):
        devilry_group_mommy_factories.feedbackset_first_try_published(
            group__parentnode__students_can_see_points=True,
            grading_points=1)
        testgroup = AssignmentGroup.objects\
            .annotate_with_is_corrected()\
            .annotate_with_grading_points()\
            .first()
        selector = htmls.S(devilry_listbuilder.assignmentgroup.PeriodAdminItemValue(
            value=testgroup, assignment=testgroup.assignment).render())
        self.assertEqual(
            'Grade: passed (1/1)',
            selector.one('.devilry-cradmin-groupitemvalue-grade').alltext_normalized)


class TestSubjectAdminItemValue(test.TestCase):
    def test_name(self):
        testgroup = mommy.make('core.AssignmentGroup')
        mommy.make('core.Candidate',
                   assignment_group=testgroup,
                   relatedstudent__user__fullname='Test User',
                   relatedstudent__user__shortname='testuser@example.com')
        selector = htmls.S(devilry_listbuilder.assignmentgroup.SubjectAdminItemValue(
            value=testgroup, assignment=testgroup.assignment).render())
        self.assertEqual(
            'Test User(testuser@example.com)',
            selector.one('.django-cradmin-listbuilder-itemvalue-titledescription-title').alltext_normalized)

    def test_name_semi_anonymous_is_not_anonymized(self):
        testgroup = mommy.make('core.AssignmentGroup',
                               parentnode__anonymizationmode=Assignment.ANONYMIZATIONMODE_SEMI_ANONYMOUS)
        mommy.make('core.Candidate',
                   assignment_group=testgroup,
                   relatedstudent__user__fullname='Test User',
                   relatedstudent__user__shortname='testuser@example.com')
        selector = htmls.S(devilry_listbuilder.assignmentgroup.SubjectAdminItemValue(
            value=testgroup, assignment=testgroup.assignment).render())
        self.assertEqual(
            'Test User(testuser@example.com)',
            selector.one('.django-cradmin-listbuilder-itemvalue-titledescription-title').alltext_normalized)

    def test_fully_anonymous_is_not_allowed(self):
        testgroup = mommy.make('core.AssignmentGroup',
                               parentnode__anonymizationmode=Assignment.ANONYMIZATIONMODE_FULLY_ANONYMOUS)
        with self.assertRaisesMessage(ValueError,
                                      'Can not use SubjectAdminItemValue for fully anonymous assignments. '
                                      'Use FullyAnonymousSubjectAdminItemValue istead.'):
            devilry_listbuilder.assignmentgroup.SubjectAdminItemValue(value=testgroup, assignment=testgroup.assignment)

    def test_examiners(self):
        testgroup = mommy.make('core.AssignmentGroup')
        mommy.make('core.Examiner',
                   assignmentgroup=testgroup,
                   relatedexaminer__user__fullname='Test User',
                   relatedexaminer__user__shortname='testuser@example.com')
        selector = htmls.S(devilry_listbuilder.assignmentgroup.SubjectAdminItemValue(
            value=testgroup, assignment=testgroup.assignment).render())
        self.assertEqual(
            'Test User(testuser@example.com)',
            selector.one('.devilry-cradmin-groupitemvalue-examiners-names').alltext_normalized)

    def test_examiners_semi_anonymous(self):
        testgroup = mommy.make('core.AssignmentGroup',
                               parentnode__anonymizationmode=Assignment.ANONYMIZATIONMODE_SEMI_ANONYMOUS)
        mommy.make('core.Examiner',
                   assignmentgroup=testgroup,
                   relatedexaminer__user__fullname='Test User',
                   relatedexaminer__user__shortname='testuser@example.com')
        selector = htmls.S(devilry_listbuilder.assignmentgroup.SubjectAdminItemValue(
            value=testgroup, assignment=testgroup.assignment).render())
        self.assertEqual(
            'Test User(testuser@example.com)',
            selector.one('.devilry-cradmin-groupitemvalue-examiners-names').alltext_normalized)

    def test_grade_students_can_see_points_false(self):
        devilry_group_mommy_factories.feedbackset_first_try_published(
            group__parentnode__students_can_see_points=False,
            grading_points=1)
        testgroup = AssignmentGroup.objects\
            .annotate_with_is_corrected()\
            .annotate_with_grading_points()\
            .first()
        selector = htmls.S(devilry_listbuilder.assignmentgroup.SubjectAdminItemValue(
            value=testgroup, assignment=testgroup.assignment).render())
        self.assertEqual(
            'Grade: passed (1/1)',
            selector.one('.devilry-cradmin-groupitemvalue-grade').alltext_normalized)

    def test_grade_students_can_see_points_true(self):
        devilry_group_mommy_factories.feedbackset_first_try_published(
            group__parentnode__students_can_see_points=True,
            grading_points=1)
        testgroup = AssignmentGroup.objects\
            .annotate_with_is_corrected()\
            .annotate_with_grading_points()\
            .first()
        selector = htmls.S(devilry_listbuilder.assignmentgroup.SubjectAdminItemValue(
            value=testgroup, assignment=testgroup.assignment).render())
        self.assertEqual(
            'Grade: passed (1/1)',
            selector.one('.devilry-cradmin-groupitemvalue-grade').alltext_normalized)


class TestDepartmentAdminItemValue(test.TestCase):
    def test_name(self):
        testgroup = mommy.make('core.AssignmentGroup')
        mommy.make('core.Candidate',
                   assignment_group=testgroup,
                   relatedstudent__user__fullname='Test User',
                   relatedstudent__user__shortname='testuser@example.com')
        selector = htmls.S(devilry_listbuilder.assignmentgroup.DepartmentAdminItemValue(
            value=testgroup, assignment=testgroup.assignment).render())
        self.assertEqual(
            'Test User(testuser@example.com)',
            selector.one('.django-cradmin-listbuilder-itemvalue-titledescription-title').alltext_normalized)

    def test_name_semi_anonymous_is_not_anoymized(self):
        testgroup = mommy.make('core.AssignmentGroup',
                               parentnode__anonymizationmode=Assignment.ANONYMIZATIONMODE_SEMI_ANONYMOUS)
        mommy.make('core.Candidate',
                   assignment_group=testgroup,
                   relatedstudent__user__fullname='Test User',
                   relatedstudent__user__shortname='testuser@example.com')
        selector = htmls.S(devilry_listbuilder.assignmentgroup.DepartmentAdminItemValue(
            value=testgroup, assignment=testgroup.assignment).render())
        self.assertEqual(
            'Test User(testuser@example.com)',
            selector.one('.django-cradmin-listbuilder-itemvalue-titledescription-title').alltext_normalized)

    def test_name_fully_anonymous_is_not_anoymized(self):
        testgroup = mommy.make('core.AssignmentGroup',
                               parentnode__anonymizationmode=Assignment.ANONYMIZATIONMODE_FULLY_ANONYMOUS)
        mommy.make('core.Candidate',
                   assignment_group=testgroup,
                   relatedstudent__user__fullname='Test User',
                   relatedstudent__user__shortname='testuser@example.com')
        selector = htmls.S(devilry_listbuilder.assignmentgroup.DepartmentAdminItemValue(
            value=testgroup, assignment=testgroup.assignment).render())
        self.assertEqual(
            'Test User(testuser@example.com)',
            selector.one('.django-cradmin-listbuilder-itemvalue-titledescription-title').alltext_normalized)

    def test_examiners(self):
        testgroup = mommy.make('core.AssignmentGroup')
        mommy.make('core.Examiner',
                   assignmentgroup=testgroup,
                   relatedexaminer__user__fullname='Test User',
                   relatedexaminer__user__shortname='testuser@example.com')
        selector = htmls.S(devilry_listbuilder.assignmentgroup.DepartmentAdminItemValue(
            value=testgroup, assignment=testgroup.assignment).render())
        self.assertEqual(
            'Test User(testuser@example.com)',
            selector.one('.devilry-cradmin-groupitemvalue-examiners-names').alltext_normalized)

    def test_examiners_semi_anonymous(self):
        testgroup = mommy.make('core.AssignmentGroup',
                               parentnode__anonymizationmode=Assignment.ANONYMIZATIONMODE_SEMI_ANONYMOUS)
        mommy.make('core.Examiner',
                   assignmentgroup=testgroup,
                   relatedexaminer__user__fullname='Test User',
                   relatedexaminer__user__shortname='testuser@example.com')
        selector = htmls.S(devilry_listbuilder.assignmentgroup.DepartmentAdminItemValue(
            value=testgroup, assignment=testgroup.assignment).render())
        self.assertEqual(
            'Test User(testuser@example.com)',
            selector.one('.devilry-cradmin-groupitemvalue-examiners-names').alltext_normalized)

    def test_examiners_fully_anonymous(self):
        testgroup = mommy.make('core.AssignmentGroup',
                               parentnode__anonymizationmode=Assignment.ANONYMIZATIONMODE_FULLY_ANONYMOUS)
        mommy.make('core.Examiner',
                   assignmentgroup=testgroup,
                   relatedexaminer__user__fullname='Test User',
                   relatedexaminer__user__shortname='testuser@example.com')
        selector = htmls.S(devilry_listbuilder.assignmentgroup.DepartmentAdminItemValue(
            value=testgroup, assignment=testgroup.assignment).render())
        self.assertEqual(
            'Test User(testuser@example.com)',
            selector.one('.devilry-cradmin-groupitemvalue-examiners-names').alltext_normalized)

    def test_grade_students_can_see_points_false(self):
        devilry_group_mommy_factories.feedbackset_first_try_published(
            group__parentnode__students_can_see_points=False,
            grading_points=1)
        testgroup = AssignmentGroup.objects\
            .annotate_with_is_corrected()\
            .annotate_with_grading_points()\
            .first()
        selector = htmls.S(devilry_listbuilder.assignmentgroup.DepartmentAdminItemValue(
            value=testgroup, assignment=testgroup.assignment).render())
        self.assertEqual(
            'Grade: passed (1/1)',
            selector.one('.devilry-cradmin-groupitemvalue-grade').alltext_normalized)

    def test_grade_students_can_see_points_true(self):
        devilry_group_mommy_factories.feedbackset_first_try_published(
            group__parentnode__students_can_see_points=True,
            grading_points=1)
        testgroup = AssignmentGroup.objects\
            .annotate_with_is_corrected()\
            .annotate_with_grading_points()\
            .first()
        selector = htmls.S(devilry_listbuilder.assignmentgroup.DepartmentAdminItemValue(
            value=testgroup, assignment=testgroup.assignment).render())
        self.assertEqual(
            'Grade: passed (1/1)',
            selector.one('.devilry-cradmin-groupitemvalue-grade').alltext_normalized)


class MockItemValue(devilry_listbuilder.assignmentgroup.AbstractItemValue):
    def get_devilryrole(self):
        return 'student'  # Should not affect any of the tests that uses this class


class TestItemValue(test.TestCase):
    def test_status_is_corrected(self):
        devilry_group_mommy_factories.feedbackset_first_try_published(
            grading_points=1)
        testgroup = AssignmentGroup.objects.annotate_with_is_corrected().first()
        selector = htmls.S(MockItemValue(value=testgroup, assignment=testgroup.assignment).render())
        self.assertFalse(selector.exists('.devilry-cradmin-groupitemvalue-status'))

    def test_status_is_waiting_for_feedback(self):
        devilry_group_mommy_factories.feedbackset_first_try_unpublished(
            group__parentnode=mommy.make_recipe('devilry.apps.core.assignment_activeperiod_start'))
        testgroup = AssignmentGroup.objects.annotate_with_is_waiting_for_feedback().first()
        selector = htmls.S(MockItemValue(value=testgroup, assignment=testgroup.assignment).render())
        self.assertEqual(
            'Status: waiting for feedback',
            selector.one('.devilry-cradmin-groupitemvalue-status').alltext_normalized)

    def test_status_is_waiting_for_deliveries(self):
        devilry_group_mommy_factories.feedbackset_first_try_unpublished(
            group__parentnode=mommy.make_recipe('devilry.apps.core.assignment_activeperiod_start',
                                                first_deadline=timezone.now() + timedelta(days=2)))
        testgroup = AssignmentGroup.objects.annotate_with_is_waiting_for_deliveries().first()
        selector = htmls.S(MockItemValue(value=testgroup, assignment=testgroup.assignment).render())
        self.assertEqual(
            'Status: waiting for deliveries',
            selector.one('.devilry-cradmin-groupitemvalue-status').alltext_normalized)

    def test_grade_not_available_unless_corrected(self):
        devilry_group_mommy_factories.feedbackset_first_try_unpublished()
        testgroup = AssignmentGroup.objects.annotate_with_is_corrected().first()
        selector = htmls.S(MockItemValue(value=testgroup, assignment=testgroup.assignment).render())
        self.assertFalse(selector.exists('.devilry-cradmin-groupitemvalue-grade'))