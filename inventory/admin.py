from django.contrib import admin
from .models import Category, Department, Order, OrderItem, InventoryItem

class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'parent')
    search_fields = ('name',)
    list_filter = ('parent',)

admin.site.register(Category, CategoryAdmin)

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 1

class OrderAdmin(admin.ModelAdmin):
    inlines = [OrderItemInline]

admin.site.register(Department)
admin.site.register(Order, OrderAdmin)

@admin.register(InventoryItem)
class InventoryItemAdmin(admin.ModelAdmin):
    list_display = ('name', 'quantity', 'category')
    search_fields = ('name',)
    list_filter = ('category',)