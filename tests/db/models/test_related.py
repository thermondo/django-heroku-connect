from django.db import models

from heroku_connect.db import models as hc_models


class TestConstraintlessForeignObjectMixin:

    def test_db_constraint(self):
        class TestFK(hc_models.ConstraintlessForeignObjectMixin, models.ForeignKey):
            pass

        class Parent(models.Model):
            class Meta:
                app_label = 'test'

        class Child(models.Model):
            parent = TestFK(Parent, on_delete=models.SET_NULL)

            class Meta:
                app_label = 'test'

        assert not Child._meta.get_field('parent').db_constraint
