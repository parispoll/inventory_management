from django import forms
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy, reverse
from django.http import HttpResponse, JsonResponse
from django.views.generic import TemplateView, View, CreateView, UpdateView, DeleteView, ListView, FormView
from django.contrib.auth import authenticate, login
from django.contrib.auth.mixins import LoginRequiredMixin
from .forms import UserRegisterForm, InventoryItemForm, InventoryItemForm, InventoryItemFormSet, CategoryFormBulkEdit, OrderItemFormSet, OrderItemForm
from .models import InventoryItem, Category, Order, InventoryLog, Department, OrderItem
from inventory_management.settings import LOW_QUANTITY
from django.contrib import messages
from django.db import models  # Import models her
from django.db.models import Sum, Count, F
from django.forms import modelformset_factory, formset_factory

import logging

class Index(TemplateView):
	template_name= 'inventory/index.html'

class Dashboard(LoginRequiredMixin, View):
    def get(self, request):
        sort_by = request.GET.get('sort', 'category')  # Default sorting by 'category'

        # Validate the sort_by parameter
        if sort_by not in ['id', 'category', 'subcategory', 'name', 'quantity']:
            sort_by = 'category'  # Default to 'category' if invalid sort_by parameter

        # Fetch items with their categories and subcategories
        items = InventoryItem.objects.filter(user=request.user.id).select_related('category__parent')

        # Sort the items based on the selected option
        if sort_by == 'subcategory':
            items = items.order_by('category__parent', 'category', 'name')
        else:
            items = items.order_by(sort_by)
        
        low_inventory = InventoryItem.objects.filter(user=request.user.id, quantity__lte=LOW_QUANTITY)
        low_inventory_ids = []

        if low_inventory.count() > 0:
            if low_inventory.count() > 1:
                messages.error(request, f'{low_inventory.count()} items have low inventory')
            else:
                messages.error(request, f'{low_inventory.count()} item has low inventory')

            low_inventory_ids = low_inventory.values_list('id', flat=True)

        return render(request, 'inventory/dashboard.html', {
            'items': items,
            'low_inventory_ids': low_inventory_ids,
            'sort_by': sort_by
        })

class SignUpView(View):
	def get(self, request):
		form = UserRegisterForm()
		return render(request, 'inventory/signup.html',{'form': form})

	def post(self,request):
		form = UserRegisterForm(request.POST)

		if form.is_valid():
			form.save()
			user = authenticate(
				username=form.cleaned_data['username'],
				password=form.cleaned_data['password1']
			)

			login(request,user)
			return redirect('index')
		return render(request,'inventory/signup.html', {'form': form})


class AddItem(LoginRequiredMixin, CreateView):
	model = InventoryItem
	form_class = InventoryItemForm
	template_name = 'inventory/item_form.html'
	success_url = reverse_lazy('dashboard')

	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)
		context['categories'] = Category.objects.all()
		return context

	def form_valid(self, form):
		form.instance.user = self.request.user
		return super().form_valid(form)

class EditItem(LoginRequiredMixin, View):
    def get(self, request, item_id):
        item = get_object_or_404(InventoryItem, id=item_id, user=request.user)
        form = InventoryItemForm(instance=item)
        return render(request, 'inventory/edit_item.html', {'form': form, 'item': item})

    def post(self, request, item_id):
        item = get_object_or_404(InventoryItem, id=item_id, user=request.user)
        form = InventoryItemForm(request.POST, instance=item)
        if form.is_valid():
            form.save()
            next_url = request.GET.get('next', 'dashboard')
            return redirect(next_url)
        return render(request, 'inventory/edit_item.html', {'form': form, 'item': item})

InventoryItemFormSet = modelformset_factory(InventoryItem, form=InventoryItemForm, extra=0)

class BulkEditInventory(View):
    template_name = 'inventory/bulk_edit_inventory.html'

    def get(self, request):
        # Retrieve selected category IDs from GET parameters, default to an empty list
        selected_category_ids = request.GET.getlist('categories')

        # Fetch categories for the category selection form
        categories = Category.objects.all()
        category_form = CategoryFormBulkEdit(initial={'categories': selected_category_ids})

        # Determine which inventory items to show based on selected categories
        if selected_category_ids:
            queryset = InventoryItem.objects.filter(category__id__in=selected_category_ids)
        else:
            queryset = InventoryItem.objects.all()  # Display all items if no category is selected

        formset = InventoryItemFormSet(queryset=queryset)
        return render(request, self.template_name, {'formset': formset, 'category_form': category_form})

    def post(self, request):
        formset = InventoryItemFormSet(request.POST)
        category_form = CategoryFormBulkEdit(request.POST)
        
        if formset.is_valid() and category_form.is_valid():
            for form in formset:
                if form.has_changed():
                    user = request.user
                    instance = form.save(commit=False)
                    # Set the category field based on the initial data
                    instance.category = InventoryItem.objects.get(id=form.instance.id).category
                    for field in form.changed_data:
                        previous_value = form.initial.get(field, None)
                        new_value = getattr(instance, field, None)
                        InventoryLog.objects.create(
                            item=instance,
                            previous_quantity=previous_value if field == 'quantity' else None,
                            new_quantity=new_value if field == 'quantity' else None,
                            changed_by=user,
                        )
                    instance.save()
            messages.success(request, "Inventory items updated successfully.")
            return redirect('inventory:bulk_edit_inventory')
        else:
            messages.error(request, "There were errors in the bulk edit forms.")

        return render(request, self.template_name, {'formset': formset, 'category_form': category_form})

        return render(request, self.template_name, {'formset': formset, 'category_form': category_form})


class DeleteItem(LoginRequiredMixin, View):
    def post(self, request, pk):
        item = get_object_or_404(InventoryItem, pk=pk, user=self.request.user)
        item.delete()
        return redirect('dashboard')

class InventorySummaryReport(LoginRequiredMixin, View):
    def get(self, request):
        items = InventoryItem.objects.filter(user=self.request.user)
        total_items = items.count()
        total_quantity = items.aggregate(Sum('quantity'))['quantity__sum'] or 0

        # Get the count of items per category
        category_counts = Category.objects.filter(inventoryitem__user=self.request.user).annotate(item_count=Count('inventoryitem')).values('id', 'name', 'item_count')

        context = {
            'total_items': total_items,
            'total_quantity': total_quantity,
            'category_counts': category_counts,
        }
        return render(request, 'inventory/inventory_summary_report.html', context)


class LowStockReport(LoginRequiredMixin, View):
    def get(self, request):
        low_stock_items = InventoryItem.objects.filter(user=self.request.user, quantity__lte=LOW_QUANTITY)
        context = {
            'low_stock_items': low_stock_items,
        }
        return render(request, 'inventory/low_stock_report.html', context)

def category_list(request):
    categories = Category.objects.filter(parent__isnull=True)
    return render(request, 'category_list.html', {'categories': categories})       

class ItemsByCategoryView(LoginRequiredMixin, View):
    def get(self, request, category_id):
        category = get_object_or_404(Category, id=category_id)
        items = InventoryItem.objects.filter(category=category, user=self.request.user)
        
        context = {
            'category': category,
            'items': items,
        }
        return render(request, 'inventory/items_by_category.html', context)


class OrderListView(ListView):
    model = Order
    template_name = 'inventory/order_list.html'
    context_object_name = 'orders'

    def get_queryset(self):
        # Order by date_created in descending order
        return Order.objects.order_by('-date_created')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['departments'] = Department.objects.all()
        context['department_id'] = self.request.GET.get('department', None)
        return context

    def post(self, request, *args, **kwargs):
        import json
        data = json.loads(request.body)
        order_id = data.get('order_id')
        
        if order_id is None:
            return JsonResponse({'status': 'error', 'message': 'Order ID not provided'})

        try:
            order = Order.objects.get(id=order_id)
            # Process the order and update inventory
            for order_item in OrderItem.objects.filter(order=order):
                inventory_item = InventoryItem.objects.get(id=order_item.item.id)
                inventory_item.quantity -= order_item.quantity_ordered
                inventory_item.save()
            
            order.confirmed = True
            order.save()
            return JsonResponse({'status': 'confirmed'})
        except Order.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Order does not exist'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})

        return redirect('inventory:order-list')

class OrderDetailView(LoginRequiredMixin, View):
    def get(self, request, pk):
        order = get_object_or_404(Order, pk=pk, created_by=request.user)
        return render(request, 'inventory/order_detail.html', {'order': order})

class InventoryLogListView(ListView):
    model = InventoryLog
    template_name = 'inventory/inventory_log_list.html'
    context_object_name = 'logs'
    paginate_by = 20  # Adjust as needed

    def get_queryset(self):
        # Order by timestamp in descending order
        return InventoryLog.objects.order_by('-timestamp')



def error_page(request):
    return render(request, 'error.html', status=400)  # Adjust the template name and status as needed

def department_list_view(request):
    departments = Department.objects.all()

    context = {
        'departments': departments
    }
    return render(request, 'inventory/department_list.html', context)

def check_categories(request, department_id):
    try:
        department = Department.objects.get(id=department_id)
        categories = department.accessible_categories.all()
        categories_list = ', '.join([category.name for category in categories])
        return HttpResponse(f"Accessible Categories for Department {department.name}:  {categories_list}")
    except Department.DoesNotExist:
        return HttpResponse("Department not found.")

def department_items_view(request, department_id):
    department = get_object_or_404(Department, id=department_id)
    # Get all categories the department has access to
    categories = department.accessible_categories.all()
    # Get all items in these categories
    items = InventoryItem.objects.filter(category__in=categories)

    context = {
        'department': department,
        'items': items
    }
    return render(request, 'inventory/department_items.html', context)

def create_order_view(request, department_id):
    department = get_object_or_404(Department, id=department_id)
    accessible_categories = department.accessible_categories.all()  # Get categories accessible by the department

    # Filter inventory items based on accessible categories
    items = InventoryItem.objects.filter(category__in=accessible_categories).distinct()

    # Define a formset using modelformset_factory to correctly initialize it with the queryset
    OrderItemFormSet = modelformset_factory(
        OrderItem,
        form=OrderItemForm,
        extra=10,
        widgets={
            'item': forms.Select(attrs={'class': 'form-control'}),
            'quantity_ordered': forms.NumberInput(attrs={'min': 0, 'class': 'form-control'}),
        }
    )

    if request.method == 'POST':
        formset = OrderItemFormSet(request.POST, request.FILES, queryset=OrderItem.objects.none())
        for form in formset.forms:
            form.fields['item'].queryset = items  # Set the queryset for each form individually

        # Debugging outputs
        print("POST request received")
        print("Formset initialized with POST data")
        print("Formset data:", formset.data)

        if formset.is_valid():
            print("Formset is valid")
            order = Order.objects.create(department=department,created_by=request.user)

            for form in formset:
                if form.is_valid() and form.cleaned_data.get('item'):  # Check if the form has an item selected
                    print(f"Form is valid, form data: {form.cleaned_data}")
                    order_item = form.save(commit=False)
                    order_item.order = order
                    order_item.save()
                    print(f"OrderItem saved with ID: {order_item.id}")
            messages.success(request, 'Order created successfully!')
            return redirect('inventory:order-list')
        else:
            print(f"Formset is invalid, errors: {formset.errors}")
            messages.error(request, 'There was an error with your submission.')
    else:
        formset = OrderItemFormSet(queryset=OrderItem.objects.none())  # Pass an empty queryset
        for form in formset.forms:
            form.fields['item'].queryset = items  # Set the queryset for each form individually

    return render(request, 'inventory/create_order.html', {
        'formset': formset,
        'department': department,
    })

