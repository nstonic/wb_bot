# Generated by Django 4.2.3 on 2023-07-28 12:41

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('employers', '0007_alter_worker_inner_phone'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='department',
            name='filial',
        ),
        migrations.DeleteModel(
            name='Filial',
        ),
    ]
