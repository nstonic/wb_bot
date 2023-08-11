from django.conf import settings
from django.contrib import admin
from django.forms import BaseInlineFormSet
from django.http import HttpResponseRedirect
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.timezone import now
from django_mptt_admin.admin import DjangoMpttAdmin

from employers.models import Worker, Department, Position, Filial


@admin.register(Worker)
class WorkerAdmin(admin.ModelAdmin):
    model = Worker
    list_display = (
        'full_name',
        'position',
        'is_active'
    )
    fieldsets = [
        (
            'Личные данные',
            {
                'fields': ('last_name', 'first_name', 'middle_name', 'birth_day', 'comment'),
            },
        ),
        (
            'Контакты',
            {
                'fields': ('cell_phone', 'inner_phone', 'email', 'icq', 'tg_id'),
            },
        ),
        (
            'Рабочие данные',
            {
                'fields': ('is_active', 'has_access_to_wb_bot', 'position', 'filial', 'start_working_at', 'fired_at'),
            },
        ),
    ]
    search_fields = (
        'last_name',
        'first_name',
        'middle_name',
        'inner_phone',
        'email'
    )
    list_filter = (
        'position',
        'department',
        'filial',
        'is_active'

    )

    def save_form(self, request, form, change):
        instance = form.save(commit=False)
        if (
                not instance.is_active
                and not instance.fired_at
        ):
            instance.fired_at = now()
        return form.save(commit=False)

    def response_change(self, request, obj):
        response = super().response_change(request, obj)
        next_url = request.GET.get('next')
        next_url_is_allowed = url_has_allowed_host_and_scheme(next_url, settings.ALLOWED_HOSTS)
        if next_url and next_url_is_allowed:
            return HttpResponseRedirect(next_url)
        else:
            return response


class WorkersFormSet(BaseInlineFormSet):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if isinstance(kwargs['instance'], Position):
            self.queryset = kwargs['queryset'].filter(
                is_active=True,
                position=kwargs['instance']
            )

        if isinstance(kwargs['instance'], Department):
            self.queryset = kwargs['queryset'].filter(
                is_active=True,
                department=kwargs['instance']
            )


class WorkersInline(admin.StackedInline):
    model = Worker
    formset = WorkersFormSet
    extra = 0
    show_change_link = True
    fields = (
        'position',
    )
    readonly_fields = (
        'full_name',
    )

    def has_add_permission(self, request, obj):
        return False


@admin.register(Department)
class DepartmentAdmin(DjangoMpttAdmin):
    model = Department
    list_display = (
        'title',
    )
    fields = (
        'title',
        'chief',
        'parent',
        'description'
    )
    readonly_fields = (
        'chief',
    )
    inlines = [
        WorkersInline
    ]


@admin.register(Position)
class PositionAdmin(admin.ModelAdmin):
    model = Position
    fields = (
        'title',
        'is_chief',
        'department',
        'description'
    )
    list_display = (
        'title',
        'department'
    )
    inlines = [
        WorkersInline
    ]


@admin.register(Filial)
class FilialAdmin(admin.ModelAdmin):
    pass
