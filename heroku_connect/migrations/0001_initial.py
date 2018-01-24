# -*- coding: utf-8 -*-
# Generated by Django 1.11.9 on 2018-01-24 14:43
from __future__ import unicode_literals

import django.contrib.postgres.fields.hstore
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='TriggerLog',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False,
                                        verbose_name='ID')),
                ('created_at', models.DateTimeField(editable=False)),
                ('updated_at', models.DateTimeField(editable=False)),
                ('processed_at', models.DateTimeField(editable=False)),
                ('table_name', models.CharField(editable=False, max_length=128)),
                ('record_id', models.BigIntegerField(editable=False)),
                ('sf_id', models.CharField(db_column='sfid', editable=False, max_length=18,
                                           null=True)),
                ('action', models.CharField(
                    choices=[('DELETE', 'DELETE'), ('INSERT', 'INSERT'), ('UPDATE', 'UPDATE')],
                    editable=False,
                    max_length=7)),
                ('sf_message', models.TextField(blank=True, editable=False, null=True)),
                ('values', django.contrib.postgres.fields.hstore.HStoreField(editable=False)),
                ('old', django.contrib.postgres.fields.hstore.HStoreField(editable=False)),
                ('state', models.CharField(
                    choices=[('FAILED', 'FAILED'), ('IGNORE', 'IGNORE'), ('IGNORED', 'IGNORED'),
                             ('MERGED', 'MERGED'), ('NEW', 'NEW'), ('PENDING', 'PENDING'),
                             ('READONLY', 'READONLY'), ('REQUEUE', 'REQUEUE'),
                             ('REQUEUED', 'REQUEUED'), ('SUCCESS', 'SUCCESS')],
                    max_length=8)),
            ],
            options={
                'db_table': 'salesforce"."_trigger_log',
                'ordering': ('-created_at', '-id'),
                'get_latest_by': 'created_at',
                'abstract': False,
                'managed': False,
            },
        ),
        migrations.CreateModel(
            name='TriggerLogArchive',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False,
                                        verbose_name='ID')),
                ('created_at', models.DateTimeField(editable=False)),
                ('updated_at', models.DateTimeField(editable=False)),
                ('processed_at', models.DateTimeField(editable=False)),
                ('table_name', models.CharField(editable=False, max_length=128)),
                ('record_id', models.BigIntegerField(editable=False)),
                ('sf_id', models.CharField(db_column='sfid', editable=False, max_length=18,
                                           null=True)),
                ('action', models.CharField(
                    choices=[('DELETE', 'DELETE'), ('INSERT', 'INSERT'), ('UPDATE', 'UPDATE')],
                    editable=False,
                    max_length=7)),
                ('sf_message', models.TextField(blank=True, editable=False, null=True)),
                ('values', django.contrib.postgres.fields.hstore.HStoreField(editable=False)),
                ('old', django.contrib.postgres.fields.hstore.HStoreField(editable=False)),
                ('state', models.CharField(
                    choices=[('FAILED', 'FAILED'), ('IGNORE', 'IGNORE'), ('IGNORED', 'IGNORED'),
                             ('MERGED', 'MERGED'), ('NEW', 'NEW'), ('PENDING', 'PENDING'),
                             ('READONLY', 'READONLY'), ('REQUEUE', 'REQUEUE'),
                             ('REQUEUED', 'REQUEUED'), ('SUCCESS', 'SUCCESS')],
                    max_length=8)),
            ],
            options={
                'db_table': 'salesforce"."_trigger_log_archive',
                'ordering': ('-created_at', '-id'),
                'get_latest_by': 'created_at',
                'abstract': False,
                'managed': False,
            },
        ),
        migrations.CreateModel(
            name='ErrorTrack',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False,
                                        verbose_name='ID')),
                ('trigger_log_id', models.BigIntegerField(editable=False, unique=True)),
                ('created_at', models.DateTimeField(editable=False)),
                ('table_name', models.CharField(editable=False, max_length=128)),
                ('record_id', models.BigIntegerField(editable=False)),
                ('action', models.CharField(editable=False, max_length=7)),
                ('state', models.CharField(editable=False, max_length=8)),
                ('sf_message', models.TextField(blank=True, editable=False, null=True)),
                ('is_initial', models.BooleanField()),
            ],
        ),
    ]
