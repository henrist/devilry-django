from django.template import defaultfilters
from django.test import TestCase
from django.core.urlresolvers import reverse
import htmls
from devilry.devilry_gradingsystem.models import FeedbackDraft
from devilry.devilry_gradingsystemplugin_points.apps import PointsPluginApi

from devilry.project.develop.testhelpers.corebuilder import SubjectBuilder
from devilry.project.develop.testhelpers.corebuilder import PeriodBuilder
from devilry.project.develop.testhelpers.corebuilder import UserBuilder
from devilry.project.develop.testhelpers.soupselect import cssFind
from devilry.project.develop.testhelpers.soupselect import cssGet
from devilry.project.develop.testhelpers.soupselect import cssExists
from devilry.apps.core.models import Candidate, StaticFeedback
from devilry.utils.datetimeutils import default_timezone_datetime


class HeaderTest(object):
    def test_header(self):
        groupbuilder = self.week1builder.add_group(
            students=[self.student1],
            examiners=[self.examiner1])
        assignment = self.week1builder.assignment
        response = self._getas('examiner1', assignment.id)
        self.assertEquals(response.status_code, 200)
        html = response.content
        self.assertEquals(cssGet(html, '.page-header h1').text.strip(),
                          'Week 1')
        self.assertEquals(cssGet(html, '.page-header .subheader').text.strip(),
                          'duck1010 &mdash; active')


class TestAllGroupsOverview(TestCase, HeaderTest):
    def setUp(self):
        self.examiner1 = UserBuilder('examiner1').user
        self.examiner2 = UserBuilder('examiner2').user
        self.student1 = UserBuilder('student1', full_name="Student One").user
        self.duck1010builder = SubjectBuilder.quickadd_ducku_duck1010()
        self.week1builder = self.duck1010builder.add_6month_active_period()\
            .add_assignment('week1', long_name='Week 1')

    def _getas(self, username, assignmentid, *args, **kwargs):
        self.client.login(username=username, password='test')
        return self.client.get(reverse('devilry_examiner_allgroupsoverview',
                                       kwargs={'assignmentid': assignmentid}),
                               *args, **kwargs)

    def _postas(self, username, assignmentid, *args, **kwargs):
        self.client.login(username=username, password='test')
        return self.client.post(reverse('devilry_examiner_allgroupsoverview',
                                        kwargs={'assignmentid': assignmentid}),
                                *args, **kwargs)

    def test_404_when_not_examiner(self):
        response = self._getas('examiner1', self.week1builder.assignment.id)
        self.assertEquals(response.status_code, 404)

    def test_200_when_examiner(self):
        self.week1builder.add_group(students=[self.student1],
                                    examiners=[self.examiner2])
        assignment = self.week1builder.assignment
        response = self._getas('examiner2', assignment.id)
        self.assertEquals(response.status_code, 200)

    def test_no_deadlines(self):
        self.week1builder.add_group(students=[self.student1],
                                    examiners=[self.examiner2])
        assignment = self.week1builder.assignment
        response = self._getas('examiner2', assignment.id)
        html = response.content
        deliverystatus = cssGet(html, 
                                '.infolistingtable .group .groupinfo .deliverystatus').text.strip()
        self.assertEquals(deliverystatus, 'No deadlines')

    def test_no_deliveries_after_deadline(self):
        self.week1builder\
            .add_group(students=[self.student1], examiners=[self.examiner2])\
            .add_deadline_x_weeks_ago(weeks=1)
        assignment = self.week1builder.assignment
        response = self._getas('examiner2', assignment.id)
        html = response.content
        deliverystatus = cssGet(html,
                                '.infolistingtable .group .groupinfo .deliverystatus').text.strip()
        self.assertEquals(deliverystatus, 'Waiting for feedback(No deliveries)')

    def test_has_deliveries_after_deadline(self):
        self.week1builder\
            .add_group(students=[self.student1], examiners=[self.examiner2])\
            .add_deadline_x_weeks_ago(weeks=1)\
            .add_delivery_x_hours_before_deadline(hours=1)
        assignment = self.week1builder.assignment
        response = self._getas('examiner2', assignment.id)
        html = response.content
        deliverystatus = cssGet(html,
                                '.infolistingtable .group .groupinfo .deliverystatus').text.strip()
        self.assertEquals(deliverystatus, 'Waiting for feedback(1 delivery received)')

    def test_no_deliveries_before_deadline(self):
        self.week1builder\
            .add_group(students=[self.student1], examiners=[self.examiner2])\
            .add_deadline_in_x_weeks(weeks=1)
        assignment = self.week1builder.assignment
        response = self._getas('examiner2', assignment.id)
        html = response.content
        deliverystatus = cssGet(html,
                                '.infolistingtable .group .groupinfo .deliverystatus').text.strip()
        self.assertIn('Waiting for deliveries(No deliveries', deliverystatus)

    def test_has_deliveries_before_deadline(self):
        self.week1builder\
            .add_group(students=[self.student1], examiners=[self.examiner2])\
            .add_deadline_in_x_weeks(weeks=1)\
            .add_delivery_x_hours_before_deadline(hours=1)
        assignment = self.week1builder.assignment
        response = self._getas('examiner2', assignment.id)
        html = response.content
        deliverystatus = cssGet(html,
                                '.infolistingtable .group .groupinfo .deliverystatus').text.strip()
        self.assertIn('Waiting for deliveries(1 delivery', deliverystatus)

    def test_show_latest_feedback_draft_info_no_draft(self):
        deliverybuilder = self.week1builder\
            .add_group(students=[self.student1], examiners=[self.examiner1])\
            .add_deadline_x_weeks_ago(weeks=1)\
            .add_delivery_x_hours_before_deadline(hours=1)
        response = self._getas('examiner1', self.week1builder.assignment.id)
        selector = htmls.S(response.content)
        self.assertFalse(selector.exists('.infolistingtable .group .groupinfo .last-feedback-draft-info'))

    def test_show_latest_feedback_draft_info_draft_by_other_not_shared_feedback_drafts(self):
        deliverybuilder = self.week1builder\
            .add_group(students=[self.student1], examiners=[self.examiner1])\
            .add_deadline_x_weeks_ago(weeks=1)\
            .add_delivery_x_hours_before_deadline(hours=1)
        FeedbackDraft.objects.bulk_create([FeedbackDraft(
            delivery=deliverybuilder.delivery,
            feedbacktext_raw='Test\n*with* _markdown_.',
            feedbacktext_html='<p>Test</p>',
            points=1,
            saved_by=self.examiner2,
            save_timestamp=default_timezone_datetime(2015, 1, 1))])
        response = self._getas('examiner1', self.week1builder.assignment.id)
        selector = htmls.S(response.content)
        self.assertFalse(selector.exists('.infolistingtable .group .groupinfo .last-feedback-draft-info'))

    def test_show_latest_feedback_draft_info_draft_by_other_shared_feedback_drafts(self):
        self.week1builder.update(feedback_workflow='trusted-cooperative-feedback-editing')
        deliverybuilder = self.week1builder\
            .add_group(students=[self.student1], examiners=[self.examiner1])\
            .add_deadline_x_weeks_ago(weeks=1)\
            .add_delivery_x_hours_before_deadline(hours=1)
        FeedbackDraft.objects.bulk_create([FeedbackDraft(
            delivery=deliverybuilder.delivery,
            feedbacktext_raw='Test\n*with* _markdown_.',
            feedbacktext_html='<p>Test</p>',
            points=1,
            saved_by=self.examiner2,
            save_timestamp=default_timezone_datetime(2015, 1, 1))])
        response = self._getas('examiner1', self.week1builder.assignment.id)
        selector = htmls.S(response.content)
        self.assertTrue(selector.exists('.infolistingtable .group .groupinfo .last-feedback-draft-info'))

    def test_show_latest_feedback_draft_info_only_draft(self):
        deliverybuilder = self.week1builder\
            .add_group(students=[self.student1], examiners=[self.examiner1])\
            .add_deadline_x_weeks_ago(weeks=1)\
            .add_delivery_x_hours_before_deadline(hours=1)
        FeedbackDraft.objects.bulk_create([FeedbackDraft(
            delivery=deliverybuilder.delivery,
            feedbacktext_raw='Test\n*with* _markdown_.',
            feedbacktext_html='<p>Test</p>',
            points=1,
            saved_by=self.examiner1,
            save_timestamp=default_timezone_datetime(2015, 1, 1))])
        response = self._getas('examiner1', self.week1builder.assignment.id)
        selector = htmls.S(response.content)
        self.assertTrue(selector.exists('.infolistingtable .group .groupinfo .last-feedback-draft-info'))

    def test_show_latest_feedback_draft_info_draft_same_as_published_feedback(self):
        deliverybuilder = self.week1builder\
            .add_group(students=[self.student1], examiners=[self.examiner1])\
            .add_deadline_x_weeks_ago(weeks=1)\
            .add_delivery_x_hours_before_deadline(hours=1)
        draft = FeedbackDraft.objects.create(
            delivery=deliverybuilder.delivery,
            points=1,
            feedbacktext_html='',
            saved_by=self.examiner1)
        staticfeedback = draft.to_staticfeedback()
        staticfeedback.save()
        draft.staticfeedback = staticfeedback
        draft.save()
        response = self._getas('examiner1', self.week1builder.assignment.id)
        selector = htmls.S(response.content)
        self.assertFalse(selector.exists('.infolistingtable .group .groupinfo .last-feedback-draft-info'))

    def test_show_latest_feedback_draft_info_draft_not_same_as_published_feedback(self):
        deliverybuilder = self.week1builder\
            .add_group(students=[self.student1], examiners=[self.examiner1])\
            .add_deadline_x_weeks_ago(weeks=1)\
            .add_delivery_x_hours_before_deadline(hours=1)
        deliverybuilder.add_passed_A_feedback(saved_by=self.examiner1)
        FeedbackDraft.objects.create(
            delivery=deliverybuilder.delivery,
            points=1,
            feedbacktext_html='',
            saved_by=self.examiner1)
        response = self._getas('examiner1', self.week1builder.assignment.id)
        selector = htmls.S(response.content)
        self.assertTrue(selector.exists('.infolistingtable .group .groupinfo .last-feedback-draft-info'))

    def test_show_latest_feedback_draft_info_not_shared_feedback_drafts(self):
        deliverybuilder = self.week1builder\
            .add_group(students=[self.student1], examiners=[self.examiner1])\
            .add_deadline_x_weeks_ago(weeks=1)\
            .add_delivery_x_hours_before_deadline(hours=1)
        FeedbackDraft.objects.bulk_create([FeedbackDraft(
            delivery=deliverybuilder.delivery,
            feedbacktext_raw='Test\n*with* _markdown_.',
            feedbacktext_html='<p>Test</p>',
            points=1,
            saved_by=self.examiner1,
            save_timestamp=default_timezone_datetime(2015, 1, 1))])
        response = self._getas('examiner1', self.week1builder.assignment.id)
        selector = htmls.S(response.content)
        self.assertFalse(selector.exists('.infolistingtable .group .groupinfo .last-feedback-draft-by'))

    def test_show_latest_feedback_draft_info_shared_feedback_drafts_by_you(self):
        self.week1builder.update(feedback_workflow='trusted-cooperative-feedback-editing')
        deliverybuilder = self.week1builder\
            .add_group(students=[self.student1], examiners=[self.examiner1])\
            .add_deadline_x_weeks_ago(weeks=1)\
            .add_delivery_x_hours_before_deadline(hours=1)
        FeedbackDraft.objects.bulk_create([FeedbackDraft(
            delivery=deliverybuilder.delivery,
            feedbacktext_raw='Test\n*with* _markdown_.',
            feedbacktext_html='<p>Test</p>',
            points=1,
            saved_by=self.examiner1,
            save_timestamp=default_timezone_datetime(2015, 1, 1))])
        response = self._getas('examiner1', self.week1builder.assignment.id)
        selector = htmls.S(response.content)
        self.assertEqual(
            selector.one('.infolistingtable .group .groupinfo .last-feedback-draft-by').alltext_normalized,
            'By you,')
        self.assertTrue(selector.exists('.infolistingtable .group .groupinfo .last-feedback-draft-by-you'))
        self.assertFalse(selector.exists('.infolistingtable .group .groupinfo .last-feedback-draft-by-other'))

    def test_show_latest_feedback_draft_info_shared_feedback_drafts_by_other(self):
        deliverybuilder = self.week1builder\
            .add_group(students=[self.student1], examiners=[self.examiner1])\
            .add_deadline_x_weeks_ago(weeks=1)\
            .add_delivery_x_hours_before_deadline(hours=1)
        self.week1builder.update(feedback_workflow='trusted-cooperative-feedback-editing')
        FeedbackDraft.objects.bulk_create([FeedbackDraft(
            delivery=deliverybuilder.delivery,
            feedbacktext_raw='Test\n*with* _markdown_.',
            feedbacktext_html='<p>Test</p>',
            points=1,
            saved_by=self.examiner2,
            save_timestamp=default_timezone_datetime(2015, 1, 1))])
        response = self._getas('examiner1', self.week1builder.assignment.id)
        selector = htmls.S(response.content)
        self.assertEqual(
            selector.one('.infolistingtable .group .groupinfo .last-feedback-draft-by').alltext_normalized,
            'examiner2,')
        self.assertFalse(selector.exists('.infolistingtable .group .groupinfo .last-feedback-draft-by-you'))
        self.assertTrue(selector.exists('.infolistingtable .group .groupinfo .last-feedback-draft-by-other'))

    def test_show_latest_feedback_draft_info_savetimestamp(self):
        deliverybuilder = self.week1builder\
            .add_group(students=[self.student1], examiners=[self.examiner1])\
            .add_deadline_x_weeks_ago(weeks=1)\
            .add_delivery_x_hours_before_deadline(hours=1)
        FeedbackDraft.objects.bulk_create([FeedbackDraft(
            delivery=deliverybuilder.delivery,
            feedbacktext_raw='Test\n*with* _markdown_.',
            feedbacktext_html='<p>Test</p>',
            points=1,
            saved_by=self.examiner1,
            save_timestamp=default_timezone_datetime(2015, 1, 1))])
        response = self._getas('examiner1', self.week1builder.assignment.id)
        selector = htmls.S(response.content)
        self.assertEqual(
            selector.one('.infolistingtable .group .groupinfo .last-feedback-draft-savetimestamp').alltext_normalized,
            defaultfilters.date(default_timezone_datetime(2015, 1, 1), 'SHORT_DATETIME_FORMAT'))

    def test_show_latest_feedback_draft_info_grade(self):
        deliverybuilder = self.week1builder\
            .add_group(students=[self.student1], examiners=[self.examiner1])\
            .add_deadline_x_weeks_ago(weeks=1)\
            .add_delivery_x_hours_before_deadline(hours=1)
        FeedbackDraft.objects.bulk_create([FeedbackDraft(
            delivery=deliverybuilder.delivery,
            feedbacktext_raw='Test\n*with* _markdown_.',
            feedbacktext_html='<p>Test</p>',
            points=1,
            saved_by=self.examiner1,
            save_timestamp=default_timezone_datetime(2015, 1, 1))])
        response = self._getas('examiner1', self.week1builder.assignment.id)
        selector = htmls.S(response.content)
        self.assertEqual(
            selector.one('.infolistingtable .group .groupinfo .last-feedback-draft-grade').alltext_normalized,
            'Passed')

    def test_show_latest_feedback_draft_info_feedbacktext(self):
        deliverybuilder = self.week1builder\
            .add_group(students=[self.student1], examiners=[self.examiner1])\
            .add_deadline_x_weeks_ago(weeks=1)\
            .add_delivery_x_hours_before_deadline(hours=1)
        FeedbackDraft.objects.bulk_create([FeedbackDraft(
            delivery=deliverybuilder.delivery,
            feedbacktext_raw='Test\n*with* _markdown_.',
            feedbacktext_html='<p>Test</p>',
            points=1,
            saved_by=self.examiner1,
            save_timestamp=default_timezone_datetime(2015, 1, 1))])
        response = self._getas('examiner1', self.week1builder.assignment.id)
        selector = htmls.S(response.content)
        self.assertEqual(
            selector.one('.infolistingtable .group .groupinfo .last-feedback-draft-feedbacktext').alltext_normalized,
            'Test *with* _markdown_.')

    def test_show_latest_feedback_draft_info_no_feedbacktext(self):
        deliverybuilder = self.week1builder\
            .add_group(students=[self.student1], examiners=[self.examiner1])\
            .add_deadline_x_weeks_ago(weeks=1)\
            .add_delivery_x_hours_before_deadline(hours=1)
        FeedbackDraft.objects.bulk_create([FeedbackDraft(
            delivery=deliverybuilder.delivery,
            feedbacktext_raw='',
            points=1,
            saved_by=self.examiner1,
            save_timestamp=default_timezone_datetime(2015, 1, 1))])
        response = self._getas('examiner1', self.week1builder.assignment.id)
        selector = htmls.S(response.content)
        self.assertFalse(selector.exists('.infolistingtable .group .groupinfo .last-feedback-draft-feedbacktext'))

    def test_group_naming(self):
        self.week1builder.add_group(
            students=[self.student1],
            examiners=[self.examiner1])
        html = self._getas('examiner1', self.week1builder.assignment.id).content
        self.assertEquals(
            cssGet(html, '.infolistingtable .group .groupinfo h3 .group_long_displayname').text.strip(),
            'Student One')
        self.assertEquals(
            cssGet(html, '.infolistingtable .group .groupinfo h3 .group_short_displayname').text.strip(),
            '(student1)')

    def test_group_naming_anonymous(self):
        self.week1builder.update(anonymous=True)
        self.week1builder.add_group(
            students=[self.student1],
            examiners=[self.examiner1])
        html = self._getas('examiner1', self.week1builder.assignment.id).content
        self.assertEquals(
            cssGet(html, '.infolistingtable .group .groupinfo h3 .group_long_displayname').text.strip(),
            'candidate-id missing')
        self.assertFalse(cssExists(html,
            '.infolistingtable .group .groupinfo h3 .group_short_displayname'))

    def test_default_ordering(self):
        self.week1builder.add_group(
            students=[UserBuilder('studenta', full_name="Student A").user],
            examiners=[self.examiner1])
        self.week1builder.add_group(
            students=[UserBuilder('studentc', full_name="Student C").user],
            examiners=[self.examiner1])
        self.week1builder.add_group(
            students=[UserBuilder('studentb', full_name="Student B").user],
            examiners=[self.examiner1])
        html = self._getas('examiner1', self.week1builder.assignment.id).content
        usernames = [username.text.strip() \
                     for username in cssFind(html, '.infolistingtable .group .groupinfo .group_short_displayname')]
        self.assertEquals(usernames, ['(studenta)', '(studentb)', '(studentc)'])

    def test_default_ordering_multiple_candidates(self):
        self.week1builder.add_group(
            students=[
                UserBuilder('studentb', full_name="Student B").user,  # NOTE: The group will be ordered by this name
                UserBuilder('studentx', full_name="Student X").user,
                UserBuilder('studentz', full_name="Student Z").user
            ],
            examiners=[self.examiner1])
        self.week1builder.add_group(
            students=[
                UserBuilder('studentd', full_name="Student D").user,
                UserBuilder('studente', full_name="Student E").user,
                UserBuilder('studenta', full_name="Student A").user  # NOTE: The group will be ordered by this name
            ],
            examiners=[self.examiner1])
        self.week1builder.add_group(
            students=[UserBuilder('studentc', full_name="Student C").user],
            examiners=[self.examiner1])
        html = self._getas('examiner1', self.week1builder.assignment.id).content
        usernames = [username.text.strip()
                     for username in cssFind(html, '.infolistingtable .group .groupinfo .group_short_displayname')]
        self.assertEquals(usernames, ['(studenta, studentd, studente)', '(studentb, studentx, studentz)', '(studentc)'])

    def test_orderby_username(self):
        self.week1builder.add_group(
            students=[UserBuilder('studenta', full_name="Student 4").user],
            examiners=[self.examiner1])
        self.week1builder.add_group(
            students=[UserBuilder('studentc', full_name="Student 0").user],
            examiners=[self.examiner1])
        self.week1builder.add_group(
            students=[UserBuilder('studentb', full_name="Student 2").user],
            examiners=[self.examiner1])
        html = self._getas('examiner1', self.week1builder.assignment.id,
                           data={'order_by': 'username'}).content
        usernames = [username.text.strip() \
                     for username in cssFind(html, '.infolistingtable .group .groupinfo .group_short_displayname')]
        self.assertEquals(usernames, ['(studenta)', '(studentb)', '(studentc)'])

    def test_orderby_username_descending(self):
        self.week1builder.add_group(
            students=[UserBuilder('studenta', full_name="Student 4").user],
            examiners=[self.examiner1])
        self.week1builder.add_group(
            students=[UserBuilder('studentc', full_name="Student 0").user],
            examiners=[self.examiner1])
        self.week1builder.add_group(
            students=[UserBuilder('studentb', full_name="Student 2").user],
            examiners=[self.examiner1])
        html = self._getas('examiner1', self.week1builder.assignment.id,
                           data={'order_by': 'username_descending'}).content
        usernames = [username.text.strip() \
                     for username in cssFind(html, '.infolistingtable .group .groupinfo .group_short_displayname')]
        self.assertEquals(usernames, ['(studentc)', '(studentb)', '(studenta)'])

    def test_orderby_fullname(self):
        self.week1builder.add_group(
            students=[UserBuilder('studenta', full_name="Student 4").user],
            examiners=[self.examiner1])
        self.week1builder.add_group(
            students=[UserBuilder('studentc', full_name="Student 0").user],
            examiners=[self.examiner1])
        self.week1builder.add_group(
            students=[UserBuilder('studentb', full_name="Student 2").user],
            examiners=[self.examiner1])
        html = self._getas('examiner1', self.week1builder.assignment.id,
                           data={'order_by': ''}).content
        usernames = [username.text.strip() \
                     for username in cssFind(html, '.infolistingtable .group .groupinfo .group_short_displayname')]
        self.assertEquals(usernames, ['(studentc)', '(studentb)', '(studenta)'])

    def test_orderby_fullname_descending(self):
        self.week1builder.add_group(
            students=[UserBuilder('studenta', full_name="Student 4").user],
            examiners=[self.examiner1])
        self.week1builder.add_group(
            students=[UserBuilder('studentc', full_name="Student 0").user],
            examiners=[self.examiner1])
        self.week1builder.add_group(
            students=[UserBuilder('studentb', full_name="Student 2").user],
            examiners=[self.examiner1])
        html = self._getas('examiner1', self.week1builder.assignment.id,
                           data={'order_by': 'name_descending'}).content
        usernames = [username.text.strip()
                     for username in cssFind(html, '.infolistingtable .group .groupinfo .group_short_displayname')]
        self.assertEquals(usernames, ['(studenta)', '(studentb)', '(studentc)'])

    def test_orderby_candidate_id(self):
        self.week1builder.update(anonymous=True)
        self.week1builder.add_group(
            candidates=[
                Candidate(student=UserBuilder('studentz').user, candidate_id='z'),
                Candidate(student=UserBuilder('studentb').user, candidate_id='b')],
            examiners=[self.examiner1])
        self.week1builder.add_group(
            candidates=[
                Candidate(student=UserBuilder('studenta').user, candidate_id='a')],
            examiners=[self.examiner1])
        self.week1builder.add_group(
            candidates=[
                Candidate(student=UserBuilder('studentc').user, candidate_id='c')],
            examiners=[self.examiner1])
        html = self._getas('examiner1', self.week1builder.assignment.id,
                           data={'order_by': 'candidate_id'}).content
        candidate_ids = [candidate_ids.text.strip()
                         for candidate_ids in cssFind(html, '.infolistingtable .group .group_long_displayname')]
        self.assertEquals(candidate_ids, ['a', 'b, z', 'c'])

    def test_orderby_invalid(self):
        self.week1builder.add_group(
            students=[UserBuilder('studenta', full_name="Student").user],
            examiners=[self.examiner1])
        response = self._getas('examiner1', self.week1builder.assignment.id,
                               data={'order_by': 'invalid'})
        self.assertEquals(response.status_code, 400)
        self.assertIn(
            'Select a valid choice. invalid is not one of the available choices',
            response.content)

    def test_examinermode_gradeplugin_notsupported(self):
        studenta = UserBuilder('studenta', full_name="Student A").user
        studentb = UserBuilder('studentb', full_name="Student B").user
        studentc = UserBuilder('studentc', full_name="Student C").user
        self.week1builder.add_group(
            students=[studenta],
            examiners=[self.examiner1])
        self.week1builder.add_group(
            students=[studentb],
            examiners=[self.examiner1])
        self.week1builder.add_group(
            students=[studentc],
            examiners=[self.examiner1])
        self.week1builder.assignment.setup_grading(
            grading_system_plugin_id=PointsPluginApi.id,
            points_to_grade_mapper='raw-points',
            passing_grade_min_points=20,
            max_points=100)
        self.week1builder.assignment.save()
        response = self._getas('examiner1', self.week1builder.assignment.id)
        html = response.content

        self.assertFalse(cssExists(html, "#div_id_examinermode"))

    def test_examinermode_gradeplugin_supported(self):
        studenta = UserBuilder('studenta', full_name="Student A").user
        studentb = UserBuilder('studentb', full_name="Student B").user
        studentc = UserBuilder('studentc', full_name="Student C").user
        self.week1builder.add_group(
            students=[studenta],
            examiners=[self.examiner1])
        self.week1builder.add_group(
            students=[studentb],
            examiners=[self.examiner1])
        self.week1builder.add_group(
            students=[studentc],
            examiners=[self.examiner1])
        response = self._getas('examiner1', self.week1builder.assignment.id)
        html = response.content

        self.assertTrue(cssExists(html, "#div_id_examinermode"))

    def test_examinermode_quick_notsupported(self):
        studenta = UserBuilder('studenta', full_name="Student A").user
        studentb = UserBuilder('studentb', full_name="Student B").user
        studentc = UserBuilder('studentc', full_name="Student C").user
        group1builder = self.week1builder.add_group(
            students=[studenta],
            examiners=[self.examiner1])
        group2builder = self.week1builder.add_group(
            students=[studentb],
            examiners=[self.examiner1])
        group3builder = self.week1builder.add_group(
            students=[studentc],
            examiners=[self.examiner1])
        self.week1builder.assignment.setup_grading(
            grading_system_plugin_id=PointsPluginApi.id,
            points_to_grade_mapper='raw-points',
            passing_grade_min_points=20,
            max_points=100)
        self.week1builder.assignment.save()
        response = self._getas('examiner1', self.week1builder.assignment.id,
                               data={'examinermode': 'quick'})
        html = response.content

        self.assertFalse(cssExists(html, "#div_id_quickfeedbackform{}-points".format(group1builder.group.id)))
        self.assertFalse(cssExists(html, "#div_id_quickfeedbackform{}-points".format(group2builder.group.id)))
        self.assertFalse(cssExists(html, "#div_id_quickfeedbackform{}-points".format(group3builder.group.id)))

    def test_examinermode_quick(self):
        studenta = UserBuilder('studenta', full_name="Student A").user
        studentb = UserBuilder('studentb', full_name="Student B").user
        group1builder = self.week1builder.add_group(
            students=[studenta],
            examiners=[self.examiner1])
        delivery = group1builder.add_deadline_in_x_weeks(weeks=1).add_delivery_x_hours_before_deadline(hours=2)
        delivery.delivery.save()
        group2builder = self.week1builder.add_group(
            students=[studentb],
            examiners=[self.examiner1])
        delivery = group2builder.add_deadline_in_x_weeks(weeks=1).add_delivery_x_hours_before_deadline(hours=2)
        delivery.delivery.save()
        response = self._getas('examiner1', self.week1builder.assignment.id,
                               data={'examinermode': 'quick'})
        html = response.content

        self.assertTrue(cssExists(html, "#div_id_quickfeedbackform{}-points".format(group1builder.group.id)))
        self.assertTrue(cssExists(html, "#div_id_quickfeedbackform{}-points".format(group2builder.group.id)))

    def test_examinermode_quick_no_deliveries(self):
        studenta = UserBuilder('studenta', full_name="Student A").user
        studentb = UserBuilder('studentb', full_name="Student B").user
        studentc = UserBuilder('studentc', full_name="Student C").user
        self.week1builder.add_group(
            students=[studenta],
            examiners=[self.examiner1])
        self.week1builder.add_group(
            students=[studentb],
            examiners=[self.examiner1])
        self.week1builder.add_group(
            students=[studentc],
            examiners=[self.examiner1])
        response = self._getas('examiner1', self.week1builder.assignment.id,
                               data={'examinermode': 'quick'})
        html = response.content

        self.assertFalse(cssExists(html, "#div_id_quickfeedbackform1-points"))
        self.assertFalse(cssExists(html, "#div_id_quickfeedbackform2-points"))
        self.assertFalse(cssExists(html, "#div_id_quickfeedbackform3-points"))

    def test_examinermode_quick_corrected(self):
        studenta = UserBuilder('studenta', full_name="Student A").user
        studentb = UserBuilder('studentb', full_name="Student B").user

        group1builder = self.week1builder.add_group(
            students=[studenta],
            examiners=[self.examiner1])
        group1builder.add_deadline_in_x_weeks(weeks=1)\
            .add_delivery_x_hours_before_deadline(hours=2)

        group2builder = self.week1builder.add_group(
            students=[studentb],
            examiners=[self.examiner1])
        group2builder.add_deadline_in_x_weeks(weeks=1)\
            .add_delivery_x_hours_before_deadline(hours=2)

        self._postas('examiner1', self.week1builder.assignment.id,
                     data={'quickfeedbackform{}-points'.format(group1builder.group.id): 1,
                           'quickfeedbackform{}-points'.format(group2builder.group.id): 0})
        self.assertEqual(
            StaticFeedback.objects.get(delivery__deadline__assignment_group=group1builder.group).points,
            1)
        self.assertEqual(
            StaticFeedback.objects.get(delivery__deadline__assignment_group=group2builder.group).points,
            0)


class TestWaitingForFeedbackOverview(TestCase, HeaderTest):
    def setUp(self):
        self.examiner1 = UserBuilder('examiner1').user
        self.examiner2 = UserBuilder('examiner2').user
        self.student1 = UserBuilder('student1', full_name="Student One").user
        self.duck1010builder = SubjectBuilder.quickadd_ducku_duck1010()
        self.week1builder = self.duck1010builder.add_6month_active_period()\
            .add_assignment('week1', long_name='Week 1')

    def _getas(self, username, assignmentid, *args, **kwargs):
        self.client.login(username=username, password='test')
        return self.client.get(reverse('devilry_examiner_waiting_for_feedback',
                                       kwargs={'assignmentid': assignmentid}),
                               *args, **kwargs)

    def test_404_when_not_examiner(self):
        response = self._getas('examiner1', self.week1builder.assignment.id)
        self.assertEquals(response.status_code, 404)

    def test_200_when_examiner(self):
        self.week1builder.add_group(students=[self.student1],
                                    examiners=[self.examiner2])
        assignment = self.week1builder.assignment
        response = self._getas('examiner2', assignment.id)
        self.assertEquals(response.status_code, 200)


class TestWaitingForDeliveriesOverview(TestCase, HeaderTest):
    def setUp(self):
        self.examiner1 = UserBuilder('examiner1').user
        self.examiner2 = UserBuilder('examiner2').user
        self.student1 = UserBuilder('student1', full_name="Student One").user
        self.duck1010builder = SubjectBuilder.quickadd_ducku_duck1010()
        self.week1builder = self.duck1010builder.add_6month_active_period()\
            .add_assignment('week1', long_name='Week 1')

    def _getas(self, username, assignmentid, *args, **kwargs):
        self.client.login(username=username, password='test')
        return self.client.get(reverse('devilry_examiner_waiting_for_deliveries',
                                       kwargs={'assignmentid': assignmentid}),
                               *args, **kwargs)

    def test_404_when_not_examiner(self):
        response = self._getas('examiner1', self.week1builder.assignment.id)
        self.assertEquals(response.status_code, 404)

    def test_200_when_examiner(self):
        self.week1builder.add_group(students=[self.student1],
                                    examiners=[self.examiner2])
        assignment = self.week1builder.assignment
        response = self._getas('examiner2', assignment.id)
        self.assertEquals(response.status_code, 200)


class TestCorrectedOverview(TestCase, HeaderTest):
    def setUp(self):
        self.examiner1 = UserBuilder('examiner1').user
        self.examiner2 = UserBuilder('examiner2').user
        self.student1 = UserBuilder('student1', full_name="Student One").user
        self.duck1010builder = SubjectBuilder.quickadd_ducku_duck1010()
        self.week1builder = self.duck1010builder.add_6month_active_period()\
            .add_assignment('week1', long_name='Week 1')

    def _getas(self, username, assignmentid, *args, **kwargs):
        self.client.login(username=username, password='test')
        return self.client.get(reverse('devilry_examiner_corrected',
                                       kwargs={'assignmentid': assignmentid}),
                               *args, **kwargs)

    def test_404_when_not_examiner(self):
        response = self._getas('examiner1', self.week1builder.assignment.id)
        self.assertEquals(response.status_code, 404)

    def test_200_when_examiner(self):
        self.week1builder.add_group(students=[self.student1],
                                    examiners=[self.examiner2])
        assignment = self.week1builder.assignment
        response = self._getas('examiner2', assignment.id)
        self.assertEquals(response.status_code, 200)




class TestWaitingForFeedbackOrAllRedirectView(TestCase):
    def setUp(self):
        self.examiner1 = UserBuilder('examiner1').user
        self.student1 = UserBuilder('student1').user
        self.week1builder = PeriodBuilder.quickadd_ducku_duck1010_active()\
            .add_assignment('week1')

    def _getas(self, username, assignmentid, *args, **kwargs):
        self.client.login(username=username, password='test')
        return self.client.get(reverse('devilry_examiner_waiting_for_feedback_or_all',
            kwargs={'assignmentid': assignmentid}), *args, **kwargs)

    def test_404_when_not_examiner(self):
        response = self._getas('examiner1', self.week1builder.assignment.id)
        self.assertEquals(response.status_code, 404)

    def test_302_when_examiner(self):
        self.week1builder.add_group(examiners=[self.examiner1])
        assignment = self.week1builder.assignment
        response = self._getas('examiner1', assignment.id)
        self.assertEquals(response.status_code, 302)

    def test_no_waiting_for_feedback_examiner(self):
        self.week1builder.add_group(examiners=[self.examiner1])
        assignment = self.week1builder.assignment
        response = self._getas('examiner1', assignment.id)
        self.assertEquals(response.status_code, 302)
        self.assertTrue(response['Location'].endswith(
            reverse('devilry_examiner_allgroupsoverview', kwargs={'assignmentid': self.week1builder.assignment.id})))

    def test_has_waiting_for_feedback_examiner(self):
        self.week1builder.add_group(examiners=[self.examiner1])\
            .add_deadline_x_weeks_ago(weeks=1)\
            .add_delivery()
        assignment = self.week1builder.assignment
        response = self._getas('examiner1', assignment.id)
        self.assertEquals(response.status_code, 302)
        self.assertTrue(response['Location'].endswith(
            reverse('devilry_examiner_waiting_for_feedback', kwargs={'assignmentid': self.week1builder.assignment.id})))
