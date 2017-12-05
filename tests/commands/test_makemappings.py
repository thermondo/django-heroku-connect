import json
import os
import tempfile

from django.core.management import call_command


class TestMakeMappings:

    @staticmethod
    def assert_mapping(mapping):
        assert mapping['mappings'] == [
            {
                'config': {
                    'access': 'read_only',
                    'fields': {
                        'A_Number__c': {},
                        'ID': {},
                        'IsDeleted': {},
                        'SystemModstamp': {},
                    },
                    'indexes': {
                        'ID': {'unique': True},
                        'SystemModstamp': {'unique': False},
                    },
                    'sf_max_daily_api_calls': 30000,
                    'sf_notify_enabled': True,
                    'sf_polling_seconds': 120,
                },
                'object_name': 'Number_Object__c',
            },
        ]

        assert mapping['connection']['app_name'] == 'ninja'
        assert mapping['connection']['organization_id'] == '1234567890'
        assert mapping['version'] == 1

    def test_stdout(self):
        path = tempfile.mkdtemp()
        file_name = os.path.join(path, 'mapping.json')
        with open(file_name, 'w+') as f:
            call_command('makemappings', stdout=f)

        with open(file_name) as f:
            mapping = json.load(f)
        self.assert_mapping(mapping)

    def test_file(self):
        path = tempfile.mkdtemp()
        file_name = os.path.join(path, 'mapping.json')
        call_command('makemappings', '-o', file_name)
        with open(file_name) as f:
            mapping = json.load(f)

        self.assert_mapping(mapping)
