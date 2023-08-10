# Generated by Django 4.2.3 on 2023-07-27 07:16

from django.db import migrations
import django.db.models.deletion
import mptt.fields
import phonenumber_field.modelfields


class Migration(migrations.Migration):

    dependencies = [
        ('employers', '0004_worker_department'),
    ]

    operations = [
        migrations.AlterField(
            model_name='department',
            name='parent',
            field=mptt.fields.TreeForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='childrens', to='employers.department', verbose_name='Входит в отдел'),
        ),
        migrations.AlterField(
            model_name='worker',
            name='cell_phone',
            field=phonenumber_field.modelfields.PhoneNumberField(blank=True, max_length=128, region='RU', verbose_name='Телефон'),
        ),
    ]
