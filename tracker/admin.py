from django.contrib import admin
from .models import Category, Transaction, Budget

admin.site.register(Category)
admin.site.register(Transaction)

@admin.register(Budget)
class BudgetAdmin(admin.ModelAdmin):
    list_display = ['user', 'category', 'month', 'amount']
    list_filter = ['user', 'month']