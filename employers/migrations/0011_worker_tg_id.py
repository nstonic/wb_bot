# Generated by Django 4.2.3 on 2023-08-10 11:57

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('employers', '0010_worker_has_access_to_wb_bot'),
    ]

    operations = [
        migrations.AddField(
            model_name='worker',
            name='tg_id',
            field=models.IntegerField(blank=True, null=True, verbose_name='ID в телеграмме'),
        ),
    ]
