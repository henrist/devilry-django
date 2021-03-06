# -*- coding: utf-8 -*-
# Generated by Django 1.9.9 on 2017-02-03 12:39
from __future__ import unicode_literals

from django.db import migrations
from django.db.models import F


def datamigrate_update_for_none_values_in_assignment_firstdeadline(apps, schema_editor):
    assignment_model = apps.get_model('core', 'Assignment')

    # We need to iterate and save it, since a joined F() on
    # assignment__parentnode__end_time wont work
    for assignment in assignment_model.objects.filter(first_deadline=None):
        assignment.first_deadline = assignment.parentnode.end_time
        assignment.save()


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0031_auto_20170125_1601'),
    ]

    operations = [
        migrations.RunPython(datamigrate_update_for_none_values_in_assignment_firstdeadline)
    ]
