# Generated by Django 4.2.3 on 2023-07-25 11:50

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tg', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='User',
            fields=[
                ('telegram_id', models.IntegerField(primary_key=True, serialize=False, verbose_name='ID в телеграмм')),
                ('full_name', models.CharField(max_length=128, verbose_name='Полное имя')),
                ('manager', models.BooleanField(blank=True, default=False, null=True, verbose_name='Управления поставками')),
                ('admin', models.BooleanField(default=False, verbose_name='Получение логов')),
            ],
        ),
    ]
