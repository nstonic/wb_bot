from django.db import models
from mptt.fields import TreeForeignKey
from mptt.models import MPTTModel
from mptt.querysets import TreeQuerySet
from phonenumber_field.modelfields import PhoneNumberField


class Filial(models.Model):
    title = models.CharField(
        'Название',
        max_length=32
    )
    address = models.CharField(
        'Адрес',
        max_length=256
    )
    city = models.CharField(
        'Город',
        max_length=64
    )
    description = models.TextField(
        'Описание',
        blank=True
    )

    def __str__(self):
        return self.title

    class Meta:
        verbose_name = 'Филиал'
        verbose_name_plural = 'Филиалы'


class Department(MPTTModel):
    title = models.CharField(
        'Название',
        max_length=128
    )
    parent = TreeForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='childs',
        verbose_name='Входит в отдел'
    )
    description = models.TextField(
        'Описание',
        blank=True
    )

    objects = TreeQuerySet(model='Department').as_manager()

    def __str__(self):
        return self.title

    @property
    def chief(self):
        return Worker.objects.filter(department=self, position__is_chief=True).first()

    chief.fget.short_description = 'Руководитель'

    class Meta:
        verbose_name = 'Отдел'
        verbose_name_plural = 'Отделы'


class Position(models.Model):
    title = models.CharField(
        'Название',
        max_length=128
    )
    is_chief = models.BooleanField(
        'Руководящая должность',
        default=False
    )
    description = models.TextField(
        'Описание',
        blank=True
    )
    department = models.ForeignKey(
        Department,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name='Отдел',
        related_name='positions'
    )

    def __str__(self):
        return self.title

    class Meta:
        verbose_name = 'Должность'
        verbose_name_plural = 'Должности'

    def save(self, *args, **kwargs):
        if self.is_chief:
            try:
                current_chief = Position.objects.get(is_chief=True, department=self.department)
                if not self == current_chief:
                    current_chief.is_chief = False
                    current_chief.save()
            except Position.DoesNotExist:
                pass
            except Position.MultipleObjectsReturned:
                current_chiefs = Position.objects.filter(is_chief=True, department=self.department)
                for current_chief in current_chiefs:
                    current_chief.is_chief = False
                    current_chief.save()
        super().save(*args, **kwargs)


class Worker(models.Model):
    first_name = models.CharField(
        'Имя',
        max_length=64
    )
    last_name = models.CharField(
        'Фамилия',
        max_length=64
    )
    middle_name = models.CharField(
        'Отчество',
        max_length=64,
        blank=True
    )
    birth_day = models.DateField(
        'День рождения'
    )
    cell_phone = PhoneNumberField(
        'Телефон',
        region='RU',
        blank=True
    )
    inner_phone = models.PositiveSmallIntegerField(
        'Внутренний номер',
        null=True,
        blank=True
    )
    email = models.EmailField(
        'Email',
        null=True,
        blank=True
    )
    icq = models.CharField(
        'ICQ',
        max_length=64,
        blank=True
    )
    position = models.ForeignKey(
        Position,
        on_delete=models.PROTECT,
        null=True,
        verbose_name='Должность',
        related_name='workers'
    )
    department = models.ForeignKey(
        Department,
        on_delete=models.PROTECT,
        null=True,
        related_name='workers'
    )
    filial = models.ForeignKey(
        Filial,
        on_delete=models.PROTECT,
        null=True,
        related_name='workers',
        verbose_name='Филиал'
    )
    start_working_at = models.DateField(
        'Дата начала работы'
    )
    fired_at = models.DateField(
        'Дата увольнения',
        null=True,
        blank=True
    )
    is_active = models.BooleanField(
        'Работает',
        default=True
    )
    comment = models.TextField(
        'Комментарий',
        blank=True
    )
    tg_id = models.BigIntegerField(
        'ID в телеграмме',
        blank=True,
        null=True,
        help_text='Свой id в телеграмме можно узнать написав боту @userinfobot'
    )

    has_access_to_wb_bot = models.BooleanField(
        'Имеет доступ к боту Wildberries',
        default=False
    )

    @property
    def full_name(self):
        return f'{self.last_name} {self.first_name} {self.middle_name}'

    def __str__(self):
        return self.full_name

    class Meta:
        verbose_name = 'Сотрудник'
        verbose_name_plural = 'Сотрудники'

    def save(self, *args, **kwargs):
        if self.position:
            self.department = self.position.department
        super().save(*args, **kwargs)
