from django.db import models


class User(models.Model):
    telegram_id = models.IntegerField('ID в телеграмм', primary_key=True)
    full_name = models.CharField('Полное имя', max_length=128)
    manager = models.BooleanField('Управления поставками', default=False, null=True, blank=True)
    admin = models.BooleanField('Получение логов', default=False)
    registered_at = models.DateTimeField('Зарегистрирован', auto_now_add=True)

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'
        ordering = ['-registered_at']

