from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy, reverse
from django.http import HttpResponse
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

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['departments'] = Department.objects.all()  # Fetch all departments
        context['department_id'] = self.request.GET.get('department', None)
        return context

class OrderDetailView(LoginRequiredMixin, View):
    def get(self, request, pk):
        order = get_object_or_404(Order, pk=pk, created_by=request.user)
        return render(request, 'inventory/order_detail.html', {'order': order})

class InventoryLogListView(ListView):
    model = InventoryLog
    template_name = 'inventory/inventory_log_list.html'
    context_object_name = 'logs'
    paginate_by = 20  # Adjust as needed

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
    accessible_categories = department.accessible_categories.all()  # Assuming you have a ManyToManyField or similar

    # Filter inventory items based on accessible categories
    items = InventoryItem.objects.filter(category__in=accessible_categories).distinct()

    # Define a formset with an extra form
    OrderItemFormSet = formset_factory(OrderItemForm, extra=1)
    
    if request.method == 'POST':
        formset = OrderItemFormSet(request.POST, request.FILES)
        if formset.is_valid():
            order = Order.objects.create(department=department)
            for form in formset:
                if form.is_valid():
                    order_item = form.save(commit=False)
                    order_item.order = order
                    order_item.save()
            messages.success(request, 'Order created successfully!')
            return redirect('department-items', department_id=department_id)
        else:
            messages.error(request, 'There was an error with your submission.')
    else:
        # Pass the filtered items to the formset
        formset = OrderItemFormSet()
        # Manually set the queryset for each form in the formset
        for form in formset:
            form.fields['item'].queryset = items

    return render(request, 'inventory/create_order.html', {
        'formset': formset,
        'department': department,
    })
    
class CreateOrderView(FormView):
    template_name = 'inventory/create_order.html'
    form_class = OrderItemFormSet
    success_url = reverse_lazy('orders-list')

    def get(self, request, *args, **kwargs):
        department_id = request.GET.get('department')
        if department_id:
            try:
                department = Department.objects.get(id=department_id)
                accessible_categories = department.accessible_categories.all()
                inventory_items = InventoryItem.objects.filter(category__in=accessible_categories)
            except Department.DoesNotExist:
                inventory_items = InventoryItem.objects.none()  # Handle invalid department ID
        else:
            inventory_items = InventoryItem.objects.none()  # No items if department isn't specified

        formset = OrderItemFormSet(queryset=OrderItem.objects.none(), initial=[
            {'item': item} for item in inventory_items
        ])
        return self.render_to_response(self.get_context_data(formset=formset))

    def post(self, request, *args, **kwargs):
        formset = OrderItemFormSet(request.POST)
        if formset.is_valid():
            order = Order.objects.create()
            for form in formset:
                order_item = form.save(commit=False)
                order_item.order = order
                order_item.save()
            messages.success(request, 'Order created successfully!')
            return self.form_valid(formset)
        else:
            messages.error(request, 'There was an error with your submission.')
            return self.form_invalid(formset)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['formset'] = kwargs.get('formset', None)
        return context

    def form_valid(self, formset):
        return super().form_valid(formset)

    def form_invalid(self, formset):
        return self.render_to_response(self.get_context_data(formset=formset))

