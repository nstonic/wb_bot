from django.db import models
from django.utils.datetime_safe import datetime


class Supply(models.Model):
    id = models.CharField(max_length=32, primary_key=True)
    name = models.CharField('Название', max_length=32)
    closed_at = models.DateTimeField('Закрыта', null=True, blank=True)
    created_at = models.DateTimeField('Создана')
    is_open = models.BooleanField('Открыта', default=False)
    qr_code = models.TextField(null=True, blank=True)

    class Meta:
        verbose_name = 'Поставка'
        verbose_name_plural = 'Поставки'
        ordering = ['-created_at']

    def __str__(self):
        is_done = ('Открыта', 'Закрыта')
        return f'{self.name} | {self.id} | {is_done[self.is_open]}'


class Product(models.Model):
    article = models.CharField('Артикул', max_length=255, primary_key=True)
    name = models.CharField('Название', max_length=255)
    barcode = models.CharField('Штрихкод', max_length=255)
    brand = models.CharField('Бренд', max_length=64)

    def __str__(self):
        return self.article

    class Meta:
        verbose_name = 'Товар'
        verbose_name_plural = 'Товары'
        ordering = ['article']


class Order(models.Model):
    STATUSES = (
        ('WAITING', 'В работе'),
        ('SORTED', 'Отсортировано'),
        ('SOLD', 'Получено покупателем'),
        ('CANCELED', 'Отменена'),
        ('CANCELED_BY_CLIENT', 'Отмена покупателем'),
        ('DEFECT', 'Брак'),
        ('READY_FOR_PICK_UP', 'Прибыло на ПВЗ'),
    )

    id = models.IntegerField(primary_key=True)
    supply = models.ForeignKey(Supply, on_delete=models.PROTECT, verbose_name='Поставка', null=True, blank=True)
    price = models.DecimalField('Сумма', max_digits=10, decimal_places=2)
    product = models.ForeignKey(Product, on_delete=models.PROTECT, verbose_name='Товар')
    created_at = models.DateTimeField('Дата и время закрытия')
    status = models.CharField('Статус', max_length=32, choices=STATUSES, default='WAITING')
    qr_code = models.TextField(blank=True)
    qr_code_number = models.DecimalField(
        'номер QR-кода',
        max_digits=11,
        decimal_places=4,
        blank=True,
        null=True
    )

    @property
    def created_ago(self):
        created_ago = datetime.now().timestamp() - self.created_at.timestamp()
        hours, seconds = divmod(int(created_ago), 3600)
        minutes, seconds = divmod(seconds, 60)
        return f'{hours:02.0f}ч. {minutes:02.0f}м.'

    def __str__(self):
        return f'{self.product.article} | {self.created_ago}'

    class Meta:
        verbose_name = 'Заказ'
        verbose_name_plural = 'Заказы'
        ordering = ['-created_at']
