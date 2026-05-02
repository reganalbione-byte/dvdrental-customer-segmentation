from django.contrib import admin
from .models import CustomerOLAP, ModelInfo


@admin.register(CustomerOLAP)
class CustomerOLAPAdmin(admin.ModelAdmin):
    list_display = ('customer_id', 'first_name', 'last_name', 'total_payment',
                    'rental_count', 'avg_payment', 'segment', 'is_active')
    list_filter = ('segment', 'is_active', 'store_id')
    search_fields = ('first_name', 'last_name', 'email')
    ordering = ('-total_payment',)


@admin.register(ModelInfo)
class ModelInfoAdmin(admin.ModelAdmin):
    list_display = ('model_name', 'model_type', 'accuracy', 'precision_score',
                    'recall_score', 'f1', 'trained_at')
    ordering = ('-trained_at',)
    readonly_fields = ('trained_at',)
