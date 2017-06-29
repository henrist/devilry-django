import os

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from devilry.devilry_import_v2database import modelimporters
from devilry.devilry_import_v2database.modelimporters import modelimporter_utils


class TimeExecution(object):
    def __init__(self, label, command):
        self.start_time = None
        self.label = label
        self.command = command

    def __enter__(self):
        self.start_time = timezone.now()

    def __exit__(self, ttype, value, traceback):
        end_time = timezone.now()
        duration = (end_time - self.start_time).total_seconds()
        self.command.stdout.write('{}: {}s'.format(self.label, duration))
        self.command.stdout.write('')


class Command(BaseCommand):
    args = '<output-directory>'
    help = 'Dump the entire database to a directory of json files.'

    def add_arguments(self, parser):
        parser.add_argument(
            'input-directory',
            help='The input directory - a directory created with '
                 '"devilry_dump_database_for_v3_migration" with Devilry 2.x.')
        parser.add_argument(
            '--fake',
            dest='fake', action='store_true',
            default=False,
            help='Print a summary of the import, but do not import anything.')

    def __abort_if_input_directory_does_not_exist(self):
        if self.fake:
            return

        if not os.path.exists(self.input_directory):
            self.stderr.write('The input directory, {}, does not exist. Aborting.'.format(
                self.input_directory
            ))
            raise SystemExit()

    def handle(self, *args, **options):
        self.input_directory = options['input-directory']
        self.fake = options['fake']
        v2_media_root = getattr(settings, 'DEVILRY_V2_MEDIA_ROOT', None)
        if not v2_media_root:
            self.stderr.write('WARNING: settings.DEVILRY_V2_MEDIA_ROOT is not set,'
                              'so StaticFeedback attachments will not be imported.')
        v2_delivery_file_root = getattr(settings, 'DEVILRY_V2_DELIVERY_FILE_ROOT', None)
        if not v2_delivery_file_root:
            self.stderr.write('WARNING: settings.DEVILRY_V2_DELIVERY_FILE_ROOT is not set,'
                              'so FileMeta will not be imported.')

        self.__abort_if_input_directory_does_not_exist()
        self.__verify_empty_database()
        self.__run()

    def __get_importer_classes(self):
        return [
            modelimporters.UserImporter,
            modelimporters.NodeImporter,
            modelimporters.SubjectImporter,
            modelimporters.PeriodImporter,
            modelimporters.AssignmentImporter,
            modelimporters.RelatedExaminerImporter,
            modelimporters.RelatedStudentImporter,
            modelimporters.AssignmentGroupImporter,
            modelimporters.ExaminerImporter,
            modelimporters.CandidateImporter,
            modelimporters.FeedbackSetImporter,
            modelimporters.DeliveryImporter,
            modelimporters.StaticFeedbackImporter,
            modelimporters.FileMetaImporter,
        ]

    def __iterate_importers(self):
        for importer_class in self.__get_importer_classes():
            yield importer_class(input_root=self.input_directory)

    def __verify_empty_database(self):
        if self.fake:
            return
        for importer in self.__iterate_importers():
            if importer.target_model_has_objects():
                self.stdout.write('{} objects already exists in the database. Aborting.'.format(
                    importer.prettyformat_model_name()))

    def __run(self):
        importer_classes = self.__get_importer_classes()
        for index, importer in enumerate(self.__iterate_importers(), start=1):
            self.stdout.write('Importing model {index}/{count} {model!r}'.format(
                index=index,
                count=len(importer_classes),
                model=importer.prettyformat_model_name()))
            with TimeExecution(importer.prettyformat_model_name(), self):
                with transaction.atomic():
                    importer.import_models(fake=self.fake)