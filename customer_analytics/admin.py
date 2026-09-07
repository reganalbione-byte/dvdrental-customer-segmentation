from django.contrib import admin

from .models import CustomerOLAP, ModelInfo


@admin.register(CustomerOLAP)
class CustomerOLAPAdmin(admin.ModelAdmin):
    list_display = ('customer_id', 'first_name', 'last_name', 'total_payment',
                    'rental_count', 'recency_days', 'segment', 'is_active')
    list_filter = ('segment', 'is_active', 'store_id')
    search_fields = ('first_name', 'last_name', 'email')
    ordering = ('-total_payment',)
    readonly_fields = ('created_at', 'updated_at')


@admin.register(ModelInfo)
class ModelInfoAdmin(admin.ModelAdmin):
    list_display = ('model_name', 'model_type', 'headline_metric', 'trained_at')
    ordering = ('-trained_at',)
    readonly_fields = ('trained_at',)
