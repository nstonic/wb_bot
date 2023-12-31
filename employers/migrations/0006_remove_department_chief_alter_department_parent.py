# Generated by Django 4.2.3 on 2023-07-28 10:00

from django.db import migrations
import django.db.models.deletion
import mptt.fields


class Migration(migrations.Migration):

    dependencies = [
        ('employers', '0005_alter_department_parent_alter_worker_cell_phone'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='department',
            name='chief',
        ),
        migrations.AlterField(
            model_name='department',
            name='parent',
            field=mptt.fields.TreeForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='childs', to='employers.department', verbose_name='Входит в отдел'),
        ),
    ]
