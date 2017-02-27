# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django import test

from django_cradmin import cradmin_testhelpers

from model_mommy import mommy

from devilry.devilry_admin.views.period.manage_tags import students
from devilry.devilry_dbcache.customsql import AssignmentGroupDbCacheCustomSql
from devilry.apps.core.models.relateduser import RelatedStudentTag, RelatedStudent


class TestAddTag(test.TestCase, cradmin_testhelpers.TestCaseMixin):
    viewclass = students.AddTagMultiSelectView

    def setUp(self):
        AssignmentGroupDbCacheCustomSql().initialize()

    def test_post_wrong_tags_format_in_form_1(self):
        testperiod = mommy.make('core.Period')
        teststudent1 = mommy.make('core.RelatedStudent', period=testperiod, user__shortname='teststudent1')
        mockresponse = self.mock_http200_postrequest_htmls(
            cradmin_role=testperiod,
            requestkwargs={
                'data': {
                    'selected_items': [teststudent1.id],
                    'tag_text': ',,tag1'
                }
            }
        )
        self.assertEquals(0, RelatedStudentTag.objects.count())
        self.assertEquals('Tag text must be in comma separated format! Example: tag1, tag2, tag3',
                          mockresponse.selector.one('#error_1_id_tag_text').alltext_normalized)

    def test_post_wrong_tags_format_in_form_same_tag_twice(self):
        testperiod = mommy.make('core.Period')
        teststudent1 = mommy.make('core.RelatedStudent', period=testperiod, user__shortname='teststudent1')
        mockresponse = self.mock_http200_postrequest_htmls(
            cradmin_role=testperiod,
            requestkwargs={
                'data': {
                    'selected_items': [teststudent1.id],
                    'tag_text': 'tag1, tag1'
                }
            }
        )
        self.assertEquals(0, RelatedStudentTag.objects.count())
        self.assertEquals('"tag1" occurs more than once in the form.',
                          mockresponse.selector.one('#error_1_id_tag_text').alltext_normalized)

    def test_post_add_single_tag(self):
        testperiod = mommy.make('core.Period')
        teststudent1 = mommy.make('core.RelatedStudent', period=testperiod, user__shortname='teststudent1')
        teststudent2 = mommy.make('core.RelatedStudent', period=testperiod, user__shortname='teststudent2')
        teststudent3 = mommy.make('core.RelatedStudent', period=testperiod, user__shortname='teststudent3')
        self.mock_http302_postrequest(
            cradmin_role=testperiod,
            requestkwargs={
                'data': {
                    'selected_items': [teststudent1.id, teststudent2.id, teststudent3.id],
                    'tag_text': 'tag1'
                }
            }
        )
        self.assertEquals(3, RelatedStudentTag.objects.count())

    def test_post_add_multiple_tags(self):
        testperiod = mommy.make('core.Period')
        teststudent1 = mommy.make('core.RelatedStudent', period=testperiod, user__shortname='teststudent1')
        teststudent2 = mommy.make('core.RelatedStudent', period=testperiod, user__shortname='teststudent2')
        teststudent3 = mommy.make('core.RelatedStudent', period=testperiod, user__shortname='teststudent3')
        self.mock_http302_postrequest(
            cradmin_role=testperiod,
            requestkwargs={
                'data': {
                    'selected_items': [teststudent1.id, teststudent2.id, teststudent3.id],
                    'tag_text': 'tag1, tag2'
                }
            }
        )
        self.assertEquals(6, RelatedStudentTag.objects.count())

    def test_post_add_student_has_tag(self):
        testperiod = mommy.make('core.Period')
        teststudent1 = mommy.make('core.RelatedStudent', period=testperiod, user__shortname='teststudent1')
        teststudent2 = mommy.make('core.RelatedStudent', period=testperiod, user__shortname='teststudent2')
        teststudent3 = mommy.make('core.RelatedStudent', period=testperiod, user__shortname='teststudent3')
        teststudent4 = mommy.make('core.RelatedStudent', period=testperiod, user__shortname='teststudent4')
        mommy.make('core.RelatedStudentTag', relatedstudent=teststudent1, tag='tag1')
        self.mock_http302_postrequest(
            cradmin_role=testperiod,
            requestkwargs={
                'data': {
                    'selected_items': [teststudent1.id, teststudent2.id, teststudent3.id, teststudent4.id],
                    'tag_text': 'tag1'
                }
            }
        )
        self.assertEquals(4, RelatedStudentTag.objects.count())

    def test_post_add_tag_student_has_multiple_tags(self):
        testperiod = mommy.make('core.Period')
        teststudent = mommy.make('core.RelatedStudent', period=testperiod, user__shortname='teststudent1')
        mommy.make('core.RelatedStudentTag', relatedstudent=teststudent, tag='tag1')
        mommy.make('core.RelatedStudentTag', relatedstudent=teststudent, tag='tag3')
        self.mock_http302_postrequest(
            cradmin_role=testperiod,
            requestkwargs={
                'data': {
                    'selected_items': [teststudent.id],
                    'tag_text': 'tag1, tag2, tag3'
                }
            }
        )
        self.assertEquals(3, RelatedStudentTag.objects.count())
        self.assertEquals(3, RelatedStudent.objects.get(id=teststudent.id).relatedstudenttag_set.count())
        tags_for_student = RelatedStudentTag.objects\
            .filter(relatedstudent__id=teststudent.id)\
            .values_list('tag', flat=True)
        self.assertEquals(3, len(tags_for_student))
        self.assertIn('tag1', tags_for_student)
        self.assertIn('tag2', tags_for_student)
        self.assertIn('tag3', tags_for_student)

    def test_post_add_tag_student_has_multiple_tags_query_count(self):
        testperiod = mommy.make('core.Period')
        teststudent = mommy.make('core.RelatedStudent', period=testperiod, user__shortname='teststudent1')
        mommy.make('core.RelatedStudentTag', relatedstudent=teststudent, tag='tag1')
        mommy.make('core.RelatedStudentTag', relatedstudent=teststudent, tag='tag3')
        with self.assertNumQueries(4):
            self.mock_http302_postrequest(
                cradmin_role=testperiod,
                requestkwargs={
                    'data': {
                        'selected_items': [teststudent.id],
                        'tag_text': 'tag1, tag2, tag3'
                    }
                }
            )
        self.assertEquals(3, RelatedStudentTag.objects.count())
        self.assertEquals(3, RelatedStudent.objects.get(id=teststudent.id).relatedstudenttag_set.count())
        tags_for_student = RelatedStudentTag.objects\
            .filter(relatedstudent__id=teststudent.id)\
            .values_list('tag', flat=True)
        self.assertEquals(3, len(tags_for_student))
        self.assertIn('tag1', tags_for_student)
        self.assertIn('tag2', tags_for_student)
        self.assertIn('tag3', tags_for_student)

    def test_post_add_tag_query_count(self):
        testperiod = mommy.make('core.Period')
        teststudent1 = mommy.make('core.RelatedStudent', period=testperiod, user__shortname='teststudent1')
        teststudent2 = mommy.make('core.RelatedStudent', period=testperiod, user__shortname='teststudent2')
        teststudent3 = mommy.make('core.RelatedStudent', period=testperiod, user__shortname='teststudent3')
        teststudent4 = mommy.make('core.RelatedStudent', period=testperiod, user__shortname='teststudent4')
        teststudent5 = mommy.make('core.RelatedStudent', period=testperiod, user__shortname='teststudent5')
        teststudent6 = mommy.make('core.RelatedStudent', period=testperiod, user__shortname='teststudent6')
        teststudent7 = mommy.make('core.RelatedStudent', period=testperiod, user__shortname='teststudent7')
        teststudent8 = mommy.make('core.RelatedStudent', period=testperiod, user__shortname='teststudent8')
        teststudent9 = mommy.make('core.RelatedStudent', period=testperiod, user__shortname='teststudent9')
        mommy.make('core.RelatedStudentTag', relatedstudent=teststudent1, tag='tag1')
        mommy.make('core.RelatedStudentTag', relatedstudent=teststudent1, tag='tag2')
        mommy.make('core.RelatedStudentTag', relatedstudent=teststudent2, tag='tag2')
        mommy.make('core.RelatedStudentTag', relatedstudent=teststudent3, tag='tag3')
        with self.assertNumQueries(4):
            self.mock_http302_postrequest(
                cradmin_role=testperiod,
                requestkwargs={
                    'data': {
                        'selected_items': [
                            teststudent1.id,
                            teststudent2.id,
                            teststudent3.id,
                            teststudent4.id,
                            teststudent5.id,
                            teststudent6.id,
                            teststudent7.id,
                            teststudent8.id,
                            teststudent9.id],
                        'tag_text': 'tag1, tag2, tag3'
                    }
                }
            )
        self.assertEquals(27, RelatedStudentTag.objects.count())


class TestRemoveTag(test.TestCase, cradmin_testhelpers.TestCaseMixin):
    viewclass = students.RemoveTagMultiselectView

    def setUp(self):
        AssignmentGroupDbCacheCustomSql().initialize()

    def test_no_students_registered_with_tag(self):
        testperiod = mommy.make('core.Period')
        mommy.make('core.RelatedStudent', user__shortname='student1', period=testperiod)
        mommy.make('core.RelatedStudent', user__shortname='student2', period=testperiod)
        mommy.make('core.RelatedStudent', user__shortname='student3', period=testperiod)
        mockresponse = self.mock_http200_getrequest_htmls(
            cradmin_role=testperiod,
            viewkwargs={
                'manage_tag': 'remove',
                'tag': 'a'
            }
        )
        self.assertNotIn('student1', mockresponse.response.content)
        self.assertNotIn('student2', mockresponse.response.content)
        self.assertNotIn('student3', mockresponse.response.content)
        self.assertEquals(0, mockresponse.selector.count('.django-cradmin-multiselect2-itemvalue'))

    def test_multiple_students_registered_with_tag(self):
        testperiod = mommy.make('core.Period')
        teststudent1 = mommy.make('core.RelatedStudent', user__shortname='student1', period=testperiod)
        teststudent2 = mommy.make('core.RelatedStudent', user__shortname='student2', period=testperiod)
        teststudent3 = mommy.make('core.RelatedStudent', user__shortname='student3', period=testperiod)
        teststudent4 = mommy.make('core.RelatedStudent', user__shortname='student4', period=testperiod)
        mommy.make('core.RelatedStudentTag', tag='a', relatedstudent=teststudent1)
        mommy.make('core.RelatedStudentTag', tag='a', relatedstudent=teststudent2)
        mommy.make('core.RelatedStudentTag', tag='a', relatedstudent=teststudent3)
        mommy.make('core.RelatedStudentTag', tag='a', relatedstudent=teststudent4)
        mockresponse = self.mock_http200_getrequest_htmls(
            cradmin_role=testperiod,
            viewkwargs={
                'manage_tag': 'remove',
                'tag': 'a'
            },
        )
        self.assertEquals(4, mockresponse.selector.count('.django-cradmin-multiselect2-itemvalue'))

    def test_only_students_with_tag_is_listed(self):
        testperiod = mommy.make('core.Period')
        teststudent1 = mommy.make('core.RelatedStudent', user__shortname='student1', period=testperiod)
        teststudent2 = mommy.make('core.RelatedStudent', user__shortname='student2', period=testperiod)
        teststudent3 = mommy.make('core.RelatedStudent', user__shortname='student3', period=testperiod)
        mommy.make('core.RelatedStudentTag', tag='a', relatedstudent=teststudent1)
        mommy.make('core.RelatedStudentTag', tag='a', relatedstudent=teststudent2)
        mommy.make('core.RelatedStudentTag', tag='b', relatedstudent=teststudent3)
        mockresponse = self.mock_http200_getrequest_htmls(
            cradmin_role=testperiod,
            viewkwargs={
                'manage_tag': 'remove',
                'tag': 'a'
            }
        )
        self.assertEquals(2, mockresponse.selector.count('.django-cradmin-multiselect2-itemvalue'))
        self.assertIn('student1', mockresponse.response.content)
        self.assertIn('student2', mockresponse.response.content)
        self.assertNotIn('student3', mockresponse.response.content)

    def test_student_not_registered_with_tag(self):
        testperiod = mommy.make('core.Period')
        mommy.make('core.RelatedStudent', user__shortname='student76', period=testperiod)
        mockresponse = self.mock_http200_getrequest_htmls(
            cradmin_role=testperiod,
            viewkwargs={
                'manage_tag': 'remove',
                'tag': 'a'
            }
        )
        self.assertNotIn('student76', mockresponse.response.content)

    def test_only_student_registered_with_tag(self):
        testperiod = mommy.make('core.Period')
        teststudent = mommy.make('core.RelatedStudent', user__shortname='student76', period=testperiod)
        mommy.make('core.RelatedStudentTag', tag='a', relatedstudent=teststudent)
        mockresponse = self.mock_http200_getrequest_htmls(
            cradmin_role=testperiod,
            viewkwargs={
                'manage_tag': 'remove',
                'tag': 'a'
            }
        )
        self.assertIn('student76', mockresponse.response.content)

    def test_does_not_render_students_with_tags_and_prefix(self):
        testperiod = mommy.make('core.Period')
        teststudent1 = mommy.make('core.RelatedStudent', user__shortname='student1', period=testperiod)
        teststudent2 = mommy.make('core.RelatedStudent', user__shortname='student2', period=testperiod)
        teststudent3 = mommy.make('core.RelatedStudent', user__shortname='student3', period=testperiod)
        mommy.make('core.RelatedStudentTag', prefix='prefix', tag='a', relatedstudent=teststudent1)
        mommy.make('core.RelatedStudentTag', prefix='prefix', tag='a', relatedstudent=teststudent2)
        mommy.make('core.RelatedStudentTag', prefix='prefix', tag='a', relatedstudent=teststudent3)
        self.assertEquals(3, RelatedStudentTag.objects.count())
        mockresponse = self.mock_http200_getrequest_htmls(
            cradmin_role=testperiod,
            viewkwargs={
                'manage_tag': 'remove',
                'tag': 'a'
            }
        )
        self.assertEquals(0, mockresponse.selector.count('.django-cradmin-multiselect2-itemvalue'))
        self.assertNotIn('student1', mockresponse.response.content)
        self.assertNotIn('student2', mockresponse.response.content)
        self.assertNotIn('student3', mockresponse.response.content)

    def test_post_delete_tag_for_student(self):
        testperiod = mommy.make('core.Period')
        teststudent = mommy.make('core.RelatedStudent', user__shortname='student76', period=testperiod)
        mommy.make('core.RelatedStudentTag', tag='a', relatedstudent=teststudent)
        self.assertEquals(1, RelatedStudentTag.objects.count())
        self.mock_http302_postrequest(
            cradmin_role=testperiod,
            viewkwargs={
                'manage_tag': 'remove',
                'tag': 'a'
            },
            requestkwargs={
                'data': {
                    'selected_items': [teststudent.id],
                }
            }
        )
        self.assertEquals(0, RelatedStudentTag.objects.count())
        self.assertEquals(0, RelatedStudent.objects.get(id=teststudent.id).relatedstudenttag_set.count())

    def test_post_delete_tag_only_for_selected_students(self):
        testperiod = mommy.make('core.Period')
        teststudent1 = mommy.make('core.RelatedStudent', user__shortname='student1', period=testperiod)
        teststudent2 = mommy.make('core.RelatedStudent', user__shortname='student2', period=testperiod)
        teststudent3 = mommy.make('core.RelatedStudent', user__shortname='student3', period=testperiod)
        mommy.make('core.RelatedStudentTag', tag='a', relatedstudent=teststudent1)
        mommy.make('core.RelatedStudentTag', tag='a', relatedstudent=teststudent2)
        mommy.make('core.RelatedStudentTag', tag='a', relatedstudent=teststudent3)
        self.assertEquals(3, RelatedStudentTag.objects.count())
        self.mock_http302_postrequest(
            cradmin_role=testperiod,
            viewkwargs={
                'manage_tag': 'remove',
                'tag': 'a'
            },
            requestkwargs={
                'data': {
                    'selected_items': [teststudent1.id, teststudent2.id],
                }
            }
        )
        self.assertEquals(1, RelatedStudentTag.objects.count())
        self.assertEquals(0, RelatedStudent.objects.get(id=teststudent1.id).relatedstudenttag_set.count())
        self.assertEquals(0, RelatedStudent.objects.get(id=teststudent2.id).relatedstudenttag_set.count())
        self.assertEquals(1, RelatedStudent.objects.get(id=teststudent3.id).relatedstudenttag_set.count())

    def test_get_query_count(self):
        testperiod = mommy.make('core.Period')
        teststudent1 = mommy.make('core.RelatedStudent', user__shortname='student1', period=testperiod)
        teststudent2 = mommy.make('core.RelatedStudent', user__shortname='student2', period=testperiod)
        teststudent3 = mommy.make('core.RelatedStudent', user__shortname='student3', period=testperiod)
        teststudent4 = mommy.make('core.RelatedStudent', user__shortname='student4', period=testperiod)
        mommy.make('core.RelatedStudentTag', tag='a', relatedstudent=teststudent1)
        mommy.make('core.RelatedStudentTag', tag='a', relatedstudent=teststudent2)
        mommy.make('core.RelatedStudentTag', tag='a', relatedstudent=teststudent3)
        mommy.make('core.RelatedStudentTag', tag='a', relatedstudent=teststudent4)
        with self.assertNumQueries(4):
            self.mock_http200_getrequest_htmls(
                cradmin_role=testperiod,
                viewkwargs={
                    'manage_tag': 'remove',
                    'tag': 'a'
                },
            )

    def test_post_delete_query_count(self):
        testperiod = mommy.make('core.Period')
        teststudent1 = mommy.make('core.RelatedStudent', user__shortname='student1', period=testperiod)
        teststudent2 = mommy.make('core.RelatedStudent', user__shortname='student2', period=testperiod)
        teststudent3 = mommy.make('core.RelatedStudent', user__shortname='student3', period=testperiod)
        teststudent4 = mommy.make('core.RelatedStudent', user__shortname='student4', period=testperiod)
        teststudent5 = mommy.make('core.RelatedStudent', user__shortname='student5', period=testperiod)
        mommy.make('core.RelatedStudentTag', tag='a', relatedstudent=teststudent1)
        mommy.make('core.RelatedStudentTag', tag='a', relatedstudent=teststudent2)
        mommy.make('core.RelatedStudentTag', tag='a', relatedstudent=teststudent3)
        mommy.make('core.RelatedStudentTag', tag='a', relatedstudent=teststudent4)
        mommy.make('core.RelatedStudentTag', tag='b', relatedstudent=teststudent5)
        self.assertEquals(5, RelatedStudentTag.objects.count())
        with self.assertNumQueries(4):
            self.mock_http302_postrequest(
                cradmin_role=testperiod,
                viewkwargs={
                    'manage_tag': 'remove',
                    'tag': 'a'
                },
                requestkwargs={
                    'data': {
                        'selected_items': [teststudent1.id, teststudent2.id, teststudent3.id, teststudent4.id],
                    }
                }
            )
        self.assertEquals(1, RelatedStudentTag.objects.count())
        self.assertEquals(0, RelatedStudent.objects.get(id=teststudent1.id).relatedstudenttag_set.count())
        self.assertEquals(0, RelatedStudent.objects.get(id=teststudent2.id).relatedstudenttag_set.count())
        self.assertEquals(0, RelatedStudent.objects.get(id=teststudent3.id).relatedstudenttag_set.count())
        self.assertEquals(0, RelatedStudent.objects.get(id=teststudent4.id).relatedstudenttag_set.count())
        self.assertEquals(1, RelatedStudent.objects.get(id=teststudent5.id).relatedstudenttag_set.count())


class TestReplaceTag(test.TestCase, cradmin_testhelpers.TestCaseMixin):
    viewclass = students.ReplaceTagMultiSelectView

    def setUp(self):
        AssignmentGroupDbCacheCustomSql().initialize()

    def test_no_users_registered_with_tag(self):
        testperiod = mommy.make('core.Period')
        mommy.make('core.RelatedStudent', user__shortname='student1', period=testperiod)
        mommy.make('core.RelatedStudent', user__shortname='student2', period=testperiod)
        mommy.make('core.RelatedStudent', user__shortname='student3', period=testperiod)
        mockresponse = self.mock_http200_getrequest_htmls(
            cradmin_role=testperiod,
            viewkwargs={
                'tag': 'a'
            }
        )
        self.assertNotIn('student1', mockresponse.response.content)
        self.assertNotIn('student2', mockresponse.response.content)
        self.assertNotIn('student3', mockresponse.response.content)
        self.assertEquals(0, mockresponse.selector.count('.django-cradmin-multiselect2-itemvalue'))

    def test_post_wrong_tags_format_in_form_1(self):
        testperiod = mommy.make('core.Period')
        teststudent = mommy.make('core.RelatedStudent', period=testperiod, user__shortname='student1')
        mockresponse = self.mock_http200_postrequest_htmls(
            cradmin_role=testperiod,
            viewkwargs={
                'tag': 'tag1'
            },
            requestkwargs={
                'data': {
                    'selected_items': [teststudent.id],
                    'tag_text': ',,tag1'
                }
            }
        )
        self.assertEquals(0, RelatedStudentTag.objects.count())
        self.assertEquals('Tag text must be in comma separated format! Example: tag1, tag2, tag3',
                          mockresponse.selector.one('#error_1_id_tag_text').alltext_normalized)

    def test_post_wrong_tags_format_in_form_same_tag_twice(self):
        testperiod = mommy.make('core.Period')
        teststudent = mommy.make('core.RelatedStudent', period=testperiod, user__shortname='student1')
        mockresponse = self.mock_http200_postrequest_htmls(
            cradmin_role=testperiod,
            viewkwargs={
                'tag': 'tag1'
            },
            requestkwargs={
                'data': {
                    'selected_items': [teststudent.id],
                    'tag_text': 'tag1, tag1'
                }
            }
        )
        self.assertEquals(0, RelatedStudentTag.objects.count())
        self.assertEquals('"tag1" occurs more than once in the form.',
                          mockresponse.selector.one('#error_1_id_tag_text').alltext_normalized)

    def test_replace_tag_for_single_user(self):
        testperiod = mommy.make('core.Period')
        teststudent = mommy.make('core.RelatedStudent', period=testperiod, user__shortname='student1')
        mommy.make('core.RelatedStudentTag', tag='a', relatedstudent=teststudent)
        self.mock_http302_postrequest(
            cradmin_role=testperiod,
            viewkwargs={
                'tag': 'a'
            },
            requestkwargs={
                'data': {
                    'selected_items': [teststudent.id],
                    'tag_text': 'b'
                }
            }
        )
        self.assertEquals(1, RelatedStudentTag.objects.count())
        self.assertNotEquals('a', RelatedStudentTag.objects.all()[0].tag)
        self.assertEquals('b', RelatedStudentTag.objects.all()[0].tag)

    def test_replace_tag_and_add_for_single_user(self):
        testperiod = mommy.make('core.Period')
        teststudent = mommy.make('core.RelatedStudent', period=testperiod, user__shortname='student1')
        mommy.make('core.RelatedStudentTag', tag='a', relatedstudent=teststudent)
        self.mock_http302_postrequest(
            cradmin_role=testperiod,
            viewkwargs={
                'tag': 'a'
            },
            requestkwargs={
                'data': {
                    'selected_items': [teststudent.id],
                    'tag_text': 'b, c, d'
                }
            }
        )
        tags = RelatedStudentTag.objects.filter(relatedstudent=teststudent)
        all_tags_list = [tag.tag for tag in tags]
        self.assertEquals(3, tags.count())
        self.assertNotIn('a', all_tags_list)
        self.assertIn('b', all_tags_list)
        self.assertIn('c', all_tags_list)
        self.assertIn('d', all_tags_list)

    def test_replace_tag_and_add_for_single_user_already_has_tag(self):
        testperiod = mommy.make('core.Period')
        teststudent = mommy.make('core.RelatedStudent', period=testperiod, user__shortname='student1')
        mommy.make('core.RelatedStudentTag', tag='a', relatedstudent=teststudent)
        mommy.make('core.RelatedStudentTag', tag='c', relatedstudent=teststudent)
        self.mock_http302_postrequest(
            cradmin_role=testperiod,
            viewkwargs={
                'tag': 'a'
            },
            requestkwargs={
                'data': {
                    'selected_items': [teststudent.id],
                    'tag_text': 'b, c, d'
                }
            }
        )
        tags = RelatedStudentTag.objects.filter(relatedstudent=teststudent)
        all_tags_list = [tag.tag for tag in tags]
        self.assertEquals(3, tags.count())
        self.assertNotIn('a', all_tags_list)
        self.assertIn('b', all_tags_list)
        self.assertIn('c', all_tags_list)
        self.assertIn('d', all_tags_list)

    def test_replace_tag_and_add_for_multiple_users_already_has_tag(self):
        testperiod = mommy.make('core.Period')
        teststudent1 = mommy.make('core.RelatedStudent', period=testperiod, user__shortname='student1')
        teststudent2 = mommy.make('core.RelatedStudent', period=testperiod, user__shortname='student2')
        teststudent3 = mommy.make('core.RelatedStudent', period=testperiod, user__shortname='student3')
        mommy.make('core.RelatedStudentTag', tag='a', relatedstudent=teststudent1)
        mommy.make('core.RelatedStudentTag', tag='a', relatedstudent=teststudent2)
        mommy.make('core.RelatedStudentTag', tag='a', relatedstudent=teststudent3)
        mommy.make('core.RelatedStudentTag', tag='c', relatedstudent=teststudent1)
        mommy.make('core.RelatedStudentTag', tag='d', relatedstudent=teststudent2)
        self.mock_http302_postrequest(
            cradmin_role=testperiod,
            viewkwargs={
                'tag': 'a'
            },
            requestkwargs={
                'data': {
                    'selected_items': [teststudent1.id, teststudent2.id, teststudent3.id],
                    'tag_text': 'b, c, d'
                }
            }
        )
        tags_student1 = RelatedStudentTag.objects.filter(relatedstudent=teststudent1)
        tags_student2 = RelatedStudentTag.objects.filter(relatedstudent=teststudent2)
        tags_student3 = RelatedStudentTag.objects.filter(relatedstudent=teststudent3)
        student1_tags_list = [tag.tag for tag in tags_student1]
        student2_tags_list = [tag.tag for tag in tags_student2]
        student3_tags_list = [tag.tag for tag in tags_student3]
        self.assertEquals(3, tags_student1.count())
        self.assertEquals(3, tags_student2.count())
        self.assertEquals(3, tags_student3.count())
        self.assertNotIn('a', student1_tags_list)
        self.assertNotIn('a', student2_tags_list)
        self.assertNotIn('a', student3_tags_list)

        self.assertIn('b', student1_tags_list)
        self.assertIn('c', student1_tags_list)
        self.assertIn('d', student1_tags_list)

        self.assertIn('b', student2_tags_list)
        self.assertIn('c', student2_tags_list)
        self.assertIn('d', student2_tags_list)

        self.assertIn('b', student3_tags_list)
        self.assertIn('c', student3_tags_list)
        self.assertIn('d', student3_tags_list)

    def test_replace_tag_and_add_user_already_has_tag_to_replace_with(self):
        testperiod = mommy.make('core.Period')
        teststudent1 = mommy.make('core.RelatedStudent', period=testperiod, user__shortname='student1')
        mommy.make('core.RelatedStudentTag', tag='a', relatedstudent=teststudent1)
        mommy.make('core.RelatedStudentTag', tag='b', relatedstudent=teststudent1)
        self.mock_http302_postrequest(
            cradmin_role=testperiod,
            viewkwargs={
                'tag': 'a'
            },
            requestkwargs={
                'data': {
                    'selected_items': [teststudent1.id],
                    'tag_text': 'b, c, d'
                }
            }
        )
        self.assertEquals(2, RelatedStudentTag.objects.count())

    def test_replace_tag_and_add_user_already_has_tag_but_is_not_first(self):
        testperiod = mommy.make('core.Period')
        teststudent = mommy.make('core.RelatedStudent', period=testperiod, user__shortname='student')
        mommy.make('core.RelatedStudentTag', tag='a', relatedstudent=teststudent)
        mommy.make('core.RelatedStudentTag', tag='b', relatedstudent=teststudent)
        self.mock_http302_postrequest(
            cradmin_role=testperiod,
            viewkwargs={
                'tag': 'a'
            },
            requestkwargs={
                'data': {
                    'selected_items': [teststudent.id],
                    'tag_text': 'c, b, d'
                }
            }
        )
        tags = RelatedStudentTag.objects.filter(relatedstudent=teststudent)
        self.assertEquals(3, tags.count())
        tags_list = [tag.tag for tag in tags]
        self.assertNotIn('a', tags_list)
        self.assertIn('c', tags_list)
        self.assertIn('b', tags_list)
        self.assertIn('d', tags_list)

    def test_replace_tag_for_multiple_users(self):
        testperiod = mommy.make('core.Period')
        teststudent1 = mommy.make('core.RelatedStudent', period=testperiod, user__shortname='student1')
        teststudent2 = mommy.make('core.RelatedStudent', period=testperiod, user__shortname='student2')
        teststudent3 = mommy.make('core.RelatedStudent', period=testperiod, user__shortname='student3')
        mommy.make('core.RelatedStudentTag', tag='a', relatedstudent=teststudent1)
        mommy.make('core.RelatedStudentTag', tag='a', relatedstudent=teststudent2)
        mommy.make('core.RelatedStudentTag', tag='a', relatedstudent=teststudent3)
        self.mock_http302_postrequest(
            cradmin_role=testperiod,
            viewkwargs={
                'manage-tag': 'replace',
                'tag': 'a'
            },
            requestkwargs={
                'data': {
                    'selected_items': [teststudent1.id, teststudent2.id, teststudent3.id],
                    'tag_text': 'b'
                }
            }
        )
        tags = RelatedStudentTag.objects.all()
        self.assertEquals(3, tags.count())
        self.assertNotEquals('a', tags[0].tag)
        self.assertNotEquals('a', tags[1].tag)
        self.assertNotEquals('a', tags[2].tag)
        self.assertEquals('b', tags[0].tag)
        self.assertEquals('b', tags[1].tag)
        self.assertEquals('b', tags[2].tag)

    def test_get_query_count(self):
        testperiod = mommy.make('core.Period')
        teststudent1 = mommy.make('core.RelatedStudent', user__shortname='student1', period=testperiod)
        teststudent2 = mommy.make('core.RelatedStudent', user__shortname='student2', period=testperiod)
        teststudent3 = mommy.make('core.RelatedStudent', user__shortname='student3', period=testperiod)
        teststudent4 = mommy.make('core.RelatedStudent', user__shortname='student4', period=testperiod)
        mommy.make('core.RelatedStudentTag', tag='a', relatedstudent=teststudent1)
        mommy.make('core.RelatedStudentTag', tag='a', relatedstudent=teststudent2)
        mommy.make('core.RelatedStudentTag', tag='a', relatedstudent=teststudent3)
        mommy.make('core.RelatedStudentTag', tag='a', relatedstudent=teststudent4)
        with self.assertNumQueries(4):
            self.mock_http200_getrequest_htmls(
                cradmin_role=testperiod,
                viewkwargs={
                    'manage_tag': 'replace',
                    'tag': 'a'
                },
            )

    def test_post_replace_query_count(self):
        testperiod = mommy.make('core.Period')
        teststudent1 = mommy.make('core.RelatedStudent', period=testperiod, user__shortname='student1')
        teststudent2 = mommy.make('core.RelatedStudent', period=testperiod, user__shortname='student2')
        teststudent3 = mommy.make('core.RelatedStudent', period=testperiod, user__shortname='student3')
        mommy.make('core.RelatedStudentTag', tag='a', relatedstudent=teststudent1)
        mommy.make('core.RelatedStudentTag', tag='a', relatedstudent=teststudent2)
        mommy.make('core.RelatedStudentTag', tag='a', relatedstudent=teststudent3)
        mommy.make('core.RelatedStudentTag', tag='c', relatedstudent=teststudent1)
        mommy.make('core.RelatedStudentTag', tag='c', relatedstudent=teststudent2)
        with self.assertNumQueries(7):
            self.mock_http302_postrequest(
                cradmin_role=testperiod,
                viewkwargs={
                    'manage-tag': 'replace',
                    'tag': 'a'
                },
                requestkwargs={
                    'data': {
                        'selected_items': [teststudent1.id, teststudent2.id, teststudent3.id],
                        'tag_text': 'b, c, d'
                    }
                }
            )
        tags_student1 = RelatedStudentTag.objects.filter(relatedstudent=teststudent1)
        tags_student2 = RelatedStudentTag.objects.filter(relatedstudent=teststudent2)
        tags_student3 = RelatedStudentTag.objects.filter(relatedstudent=teststudent3)
        self.assertEquals(3, tags_student1.count())
        self.assertEquals(3, tags_student2.count())
        self.assertEquals(3, tags_student3.count())