# Generated by Django 4.2.3 on 2023-08-19 05:55

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Product',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('article', models.CharField(max_length=64, verbose_name='Артикул')),
                ('name', models.CharField(max_length=128, verbose_name='Название')),
                ('barcode', models.CharField(max_length=32, verbose_name='Штрихкод')),
                ('brand', models.CharField(max_length=32, verbose_name='Бренд')),
            ],
            options={
                'verbose_name': 'Товар',
                'verbose_name_plural': 'Товары',
                'ordering': ['article'],
            },
        ),
        migrations.CreateModel(
            name='Supply',
            fields=[
                ('id', models.CharField(max_length=32, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=32, verbose_name='Название')),
                ('closed_at', models.DateTimeField(blank=True, null=True, verbose_name='Закрыта')),
                ('created_at', models.DateTimeField(verbose_name='Создана')),
                ('is_open', models.BooleanField(default=False, verbose_name='Открыта')),
                ('qr_code', models.TextField(blank=True, null=True)),
            ],
            options={
                'verbose_name': 'Поставка',
                'verbose_name_plural': 'Поставки',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='Order',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('price', models.DecimalField(decimal_places=2, max_digits=10, verbose_name='Сумма')),
                ('created_at', models.DateTimeField(verbose_name='Дата и время закрытия')),
                ('status', models.CharField(max_length=32, verbose_name='Статус')),
                ('qr_code', models.TextField()),
                ('qr_code_number', models.DecimalField(decimal_places=4, max_digits=11, verbose_name='номер QR-кода')),
                ('product', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='wb.product')),
                ('supply', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to='wb.supply', verbose_name='Поставка')),
            ],
            options={
                'verbose_name': 'Заказ',
                'verbose_name_plural': 'Заказы',
                'ordering': ['-created_at'],
            },
        ),
    ]
