# Generated by Django 4.2.3 on 2023-07-27 06:11

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('employers', '0002_alter_worker_start_working_at'),
    ]

    operations = [
        migrations.RenameField(
            model_name='worker',
            old_name='active',
            new_name='is_active',
        ),
    ]
