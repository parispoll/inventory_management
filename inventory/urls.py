from django.urls import path
from . import views
from .views import (
Index, SignUpView, Dashboard, AddItem, EditItem, DeleteItem, InventorySummaryReport, LowStockReport,
 ItemsByCategoryView, OrderListView, OrderDetailView, 
 InventoryLogListView,BulkEditInventory,CreateOrderView, error_page,
  check_categories, department_items_view, department_list_view, create_order_view
                )
from django.contrib.auth import views as auth_views

app_name = 'inventory'

urlpatterns = [
    path('', Index.as_view(), name='index'),
    path('dashboard/', Dashboard.as_view(), name='dashboard'),
    path('add-item/', AddItem.as_view(), name='add-item'),
    path('edit-item/<int:item_id>/', EditItem.as_view(), name='edit-item'),
    path('delete-item/<int:pk>', DeleteItem.as_view(), name='delete-item'),
    path('signup/', SignUpView.as_view(), name='signup'),
    path('login/', auth_views.LoginView.as_view(template_name='inventory/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(template_name='inventory/logout.html'), name='logout'),
    path('inventory-summary/', InventorySummaryReport.as_view(), name='inventory-summary'),
    path('low-stock/', LowStockReport.as_view(), name='low-stock'),
    path('items-by-category/<int:category_id>/', ItemsByCategoryView.as_view(), name='items-by-category'),
    path('orders/', OrderListView.as_view(), name='order-list'),
    path('orders/<int:pk>/', OrderDetailView.as_view(), name='order-detail'),
    path('inventory/logs/', InventoryLogListView.as_view(), name='inventory-log-list'),
    path('bulk-edit/', BulkEditInventory.as_view(), name='bulk_edit_inventory'),
    path('create/', CreateOrderView.as_view(), name='create-order'),
    path('error/', error_page, name='error_page'),  # Add this line
    path('check-categories/<int:department_id>/', check_categories, name='check-categories'),
    path('departments/', department_list_view, name='department-list'),
    path('department-items/<int:department_id>/', department_items_view, name='department-items'),
    path('new-order/<int:department_id>/', create_order_view, name='create-order'),
            ]

