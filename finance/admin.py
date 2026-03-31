from django.contrib import admin
from .models import Transaction, Goal

try:
    from import_export import resources
    from import_export.admin import ExportMixin
except ImportError:
    resources = None

    class ExportMixin:  # type: ignore[override]
        pass

if resources is not None:
    class TransactionResource(resources.ModelResource):
        class Meta:
            model = Transaction
            fields = ('id', 'user__username', 'amount', 'transaction_type', 'date')

else:
    class TransactionResource:
        def export(self, queryset):
            raise ImportError("import_export is required to export transactions.")

class TransactionAdmin(ExportMixin, admin.ModelAdmin):
    resource_class = TransactionResource
    list_display = ('id', 'user', 'amount', 'transaction_type', 'date')
    search_fields = ('user__username', 'amount', 'transaction_type')
    
admin.site.register(Transaction, TransactionAdmin)
admin.site.register(Goal)

