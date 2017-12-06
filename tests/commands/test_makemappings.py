import json
import os
import tempfile

from django.core.management import call_command
from django.utils import dateparse

from heroku_connect.utils import get_mapping


class TestMakeMappings:

    @staticmethod
    def assert_mapping(mapping):
        exported_at = mapping['connection']['exported_at']
        exported_at = dateparse.parse_datetime(exported_at)
        assert mapping == get_mapping(exported_at=exported_at)

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
