import json
from datetime import datetime

from django.core.management import BaseCommand
from django.utils.datetime_safe import date
from django.utils.timezone import now

from employers.models import Worker


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('file')

    def handle(self, *args, **options):
        file_path = options.get('file')
        if not file_path:
            raise NoDataException
        with open(file_path, encoding='utf8') as file:
            workers = json.load(file)
        if not workers:
            raise NoWorkersException
        for worker in workers:
            if full_name := worker.get('ФИО').split():
                if len(full_name) == 3:
                    last_name, first_name, middle_name = full_name
                elif len(full_name) == 2:
                    last_name, first_name = full_name
                    middle_name = ''
                else:
                    last_name = first_name = full_name
                    middle_name = ''
                if birth_day_line := worker.get('Дата рождения', '11/11/11'):
                    birth_day = datetime.strptime(birth_day_line, '%m/%d/%y')
                else:
                    birth_day = date(11, 11, 11)
                inner_phone = worker.get('№ вн. тел.')
                if not inner_phone.isdigit() or not isinstance(inner_phone, int):
                    inner_phone = None
                worker, created = Worker.objects.get_or_create(
                    last_name=last_name,
                    first_name=first_name,
                    middle_name=middle_name,
                    defaults={
                        'start_working_at': now(),
                        'birth_day': birth_day,
                        'cell_phone': worker.get('Сотовый'),
                        'inner_phone': inner_phone,
                        'email': worker.get('Адрес элект. почты'),
                        'icq': worker.get('ICQ'),
                        'comment': worker
                    }
                )

                created_or_updated = ('Обновлен', 'Создан')
                print(f'{created_or_updated[created]} работник {worker.last_name} {worker.first_name}')


class NoDataException(Exception):
    pass


class NoWorkersException(Exception):
    pass
