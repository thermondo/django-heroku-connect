import uuid

from django.db import NotSupportedError
from django.test import TestCase

from .models import NumberModel


class NumberModelTestCase(TestCase):
    def setUp(self):
        self.instance = NumberModel(a_number=1, external_id=uuid.UUID(int=1))
        self.pre_save_count = NumberModel.objects.count()
        self.instance.save()

    def test_save_success_on_read_write_model(self):
        final_count = NumberModel.objects.count()
        assert final_count - self.pre_save_count == 1

    def test_delete_success_on_read_write_model(self):
        post_save_count = NumberModel.objects.count()
        self.instance.delete()
        final_count = NumberModel.objects.count()
        assert post_save_count - final_count == 1

    def test_qs_update_success_on_read_write_model(self):
        NumberModel.objects.update(a_number=2)
        assert NumberModel.objects.filter(a_number=1).count() == 0
        assert NumberModel.objects.filter(a_number=2).count() == 1

    def test_qs_delete_on_read_write_model(self):
        count, _ = NumberModel.objects.filter(a_number=1).delete()
        assert count == 1
        assert NumberModel.objects.count() == 0

    def test_qs_bulk_create_on_read_write_model(self):
        new_instance = NumberModel(a_number=2, external_id=uuid.UUID(int=2))
        NumberModel.objects.bulk_create([new_instance])
        assert NumberModel.objects.count() == 2
