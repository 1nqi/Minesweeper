"""Перенос данных из SQLite в PostgreSQL (default)."""

from __future__ import annotations

import os
import tempfile

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = (
        'Экспортирует данные из SQLite (алиас sqlite_legacy) и загружает в PostgreSQL (default). '
        'Требуется: PostgreSQL в default (DATABASE_URL и т.д.) и COPY_FROM_SQLITE_PATH=путь/к/db.sqlite3'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--flush',
            action='store_true',
            help='Очистить PostgreSQL перед загрузкой (django flush: все данные приложений)',
        )

    def handle(self, *args, **options):
        if 'sqlite_legacy' not in settings.DATABASES:
            raise CommandError(
                'Добавьте в окружение COPY_FROM_SQLITE_PATH=путь\\к\\db.sqlite3 (файл старой SQLite) '
                'и убедитесь, что default — PostgreSQL. Затем выполните команду снова.'
            )

        if settings.DATABASES['default']['ENGINE'] != 'django.db.backends.postgresql':
            raise CommandError(
                'default должна указывать на PostgreSQL. Задайте DATABASE_URL (или USE_POSTGRES и POSTGRES_*).'
            )

        sqlite_name = settings.DATABASES['sqlite_legacy']['NAME']
        if not os.path.isfile(sqlite_name):
            raise CommandError(f'Файл SQLite не найден: {sqlite_name}')

        User = get_user_model()
        if User.objects.using('default').exists() and not options['flush']:
            raise CommandError(
                'В PostgreSQL уже есть пользователи. Используйте пустую БД после migrate, '
                'либо запустите с --flush (удалит все пользовательские данные в PostgreSQL!).'
            )

        if options['flush']:
            self.stdout.write(self.style.WARNING('Очистка PostgreSQL (flush)...'))
            call_command('flush', '--noinput', database='default')

        excludes = [
            'contenttypes',
            'auth.permission',
            'sessions',
            'admin.logentry',
        ]

        self.stdout.write(f'Чтение SQLite: {sqlite_name}')
        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile(
                mode='w',
                suffix='.json',
                delete=False,
                encoding='utf-8',
            ) as tmp:
                tmp_path = tmp.name
                call_command(
                    'dumpdata',
                    database='sqlite_legacy',
                    natural_foreign=True,
                    natural_primary=True,
                    exclude=excludes,
                    stdout=tmp,
                )

            self.stdout.write('Загрузка в PostgreSQL...')
            call_command('loaddata', tmp_path, database='default')
        finally:
            if tmp_path:
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass

        self.stdout.write(self.style.SUCCESS('Готово: данные перенесены в PostgreSQL.'))
