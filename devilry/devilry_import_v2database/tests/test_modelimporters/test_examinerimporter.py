from django.contrib.contenttypes.models import ContentType

from devilry.devilry_dbcache.customsql import AssignmentGroupDbCacheCustomSql
from devilry.devilry_import_v2database.models import ImportedModel
from django import test
from django.conf import settings
from django.utils.dateparse import parse_datetime

from model_mommy import mommy

from devilry.apps.core.models import Examiner, RelatedExaminer
from devilry.devilry_import_v2database.modelimporters.candidate_examiner_importer import ExaminerImporter
from .importer_testcase_mixin import ImporterTestCaseMixin


class TestExaminerImporter(ImporterTestCaseMixin, test.TestCase):
    def setUp(self):
        super(TestExaminerImporter, self).setUp()
        AssignmentGroupDbCacheCustomSql().initialize()

    def _create_examiner_dict(self, assignment_group, user):
        return {
            'pk': 156,
            'model': 'core.examiner',
            'fields': {
                'user': user.id,
                'assignmentgroup': assignment_group.id}
        }

    def test_importer(self):
        test_user = mommy.make(settings.AUTH_USER_MODEL)
        test_group = mommy.make('core.AssignmentGroup')
        self.create_v2dump(model_name='core.examiner',
                           data=self._create_examiner_dict(assignment_group=test_group, user=test_user))
        examiner_importer = ExaminerImporter(input_root=self.temp_root_dir)
        examiner_importer.import_models()
        self.assertEquals(Examiner.objects.count(), 1)
        self.assertEquals(RelatedExaminer.objects.count(), 1)

    def test_importer_pk(self):
        test_user = mommy.make(settings.AUTH_USER_MODEL)
        test_group = mommy.make('core.AssignmentGroup')
        self.create_v2dump(model_name='core.examiner',
                           data=self._create_examiner_dict(assignment_group=test_group, user=test_user))
        examiner_importer = ExaminerImporter(input_root=self.temp_root_dir)
        examiner_importer.import_models()
        examiner = Examiner.objects.first()
        self.assertEquals(examiner.pk, 156)
        self.assertEquals(examiner.id, 156)

    def test_importer_assignment_group(self):
        test_user = mommy.make(settings.AUTH_USER_MODEL)
        test_group = mommy.make('core.AssignmentGroup')
        self.create_v2dump(model_name='core.examiner',
                           data=self._create_examiner_dict(assignment_group=test_group, user=test_user))
        examiner_importer = ExaminerImporter(input_root=self.temp_root_dir)
        examiner_importer.import_models()
        examiner = Examiner.objects.first()
        self.assertEquals(examiner.assignmentgroup, test_group)

    def test_importer_related_examiner_user(self):
        test_user = mommy.make(settings.AUTH_USER_MODEL)
        test_group = mommy.make('core.AssignmentGroup')
        self.create_v2dump(model_name='core.examiner',
                           data=self._create_examiner_dict(assignment_group=test_group, user=test_user))
        examiner_importer = ExaminerImporter(input_root=self.temp_root_dir)
        examiner_importer.import_models()
        examiner = Examiner.objects.first()
        self.assertEquals(examiner.relatedexaminer.user, test_user)

    def test_importer_related_examiner_period(self):
        test_user = mommy.make(settings.AUTH_USER_MODEL)
        test_group = mommy.make('core.AssignmentGroup')
        self.create_v2dump(model_name='core.examiner',
                           data=self._create_examiner_dict(assignment_group=test_group, user=test_user))
        examiner_importer = ExaminerImporter(input_root=self.temp_root_dir)
        examiner_importer.import_models()
        examiner = Examiner.objects.first()
        self.assertEquals(examiner.relatedexaminer.period, test_group.parentnode.parentnode)

    def test_importer_imported_model_created(self):
        test_user = mommy.make(settings.AUTH_USER_MODEL)
        test_group = mommy.make('core.AssignmentGroup')
        examiner_data_dict = self._create_examiner_dict(assignment_group=test_group, user=test_user)
        self.create_v2dump(model_name='core.examiner',
                           data=examiner_data_dict)
        examiner_importer = ExaminerImporter(input_root=self.temp_root_dir)
        examiner_importer.import_models()
        examiner = Examiner.objects.first()
        self.assertEquals(ImportedModel.objects.count(), 1)
        imported_model = ImportedModel.objects.get(
            content_object_id=examiner.id,
            content_type=ContentType.objects.get_for_model(model=examiner)
        )
        self.assertEquals(imported_model.content_object, examiner)
        self.assertEquals(imported_model.data, examiner_data_dict)
