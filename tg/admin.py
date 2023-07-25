from django.contrib import admin

from tg.models import Supply, Order


@admin.register(Supply)
class SupplyAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'name',
        'is_open'
    ]
    fields = [
        'id',
        'name',
        'closed_at',
        'created_at'
    ]
    readonly_fields = [
        'id',
        'name',
        'closed_at',
        'created_at',
    ]
    list_filter = [
        'is_open'
    ]


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'product',
        'status'
    ]
    fields = [
        'id',
        'supply',
        'price',
        'product__article',
        'created_at',
        'status',
        'qr_code',
        'qr_code_number'
    ]
    readonly_fields = [
        'id',
        'supply',
        'price',
        'product',
        'created_at',
        'status',
        'qr_code',
        'qr_code_number'
    ]
    list_filter = [
        'product__article',
        'supply',
        'status'
    ]
