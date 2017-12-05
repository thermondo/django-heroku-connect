import json

from django.core.management import BaseCommand

from heroku_connect.utils import get_mapping


class Command(BaseCommand):
    """
    Return Heroku Connect mapping JSON for the entire project.

    Example::

        python manage.py makemappings -o hc_mappings.json
        heroku connect:import hc_mappings.json

    Note:
        For the example to work you will need the
        `Heroku Connect CLI Plugin`_.

    .. _`Heroku Connect CLI Plugin`: https://github.com/heroku/heroku-connect-plugin

    """

    def add_arguments(self, parser):
        parser.add_argument('-o', metavar='file_name', dest='output',
                            help='Output file name.')

    def handle(self, *args, **options):
        output = options.get('output', None)
        if output:
            f = open(output, 'w+')
        else:
            f = self.stdout

        mapping = get_mapping()

        try:
            json.dump(mapping, f)
        finally:
            f.close()
