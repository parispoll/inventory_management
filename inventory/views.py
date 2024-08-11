from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy, reverse
from django.views.generic import TemplateView, View, CreateView, UpdateView, DeleteView, ListView
from django.contrib.auth import authenticate, login
from django.contrib.auth.mixins import LoginRequiredMixin
from .forms import UserRegisterForm, InventoryItemForm, InventoryItemForm, InventoryItemFormSet
from .models import InventoryItem, Category, Order, InventoryLog
from inventory_management.settings import LOW_QUANTITY
from django.contrib import messages
from django.db import models  # Import models her
from django.db.models import Sum, Count, F

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

class CreateOrderView(LoginRequiredMixin, View):
    def get(self, request):
        department = Department.objects.get(name=request.user.profile.department)
        categories = department.categories.all()
        items = InventoryItem.objects.filter(category__in=categories)

        form = OrderForm()
        formset = OrderItemFormSet(queryset=InventoryItem.objects.none(), form_kwargs={'items': items})
        return render(request, 'inventory/create_order.html', {'form': form, 'formset': formset})

    def post(self, request):
        department = Department.objects.get(name=request.user.profile.department)
        categories = department.categories.all()
        items = InventoryItem.objects.filter(category__in=categories)

        form = OrderForm(request.POST)
        formset = OrderItemFormSet(request.POST, form_kwargs={'items': items})

        if form.is_valid() and formset.is_valid():
            order = form.save(commit=False)
            order.department = department
            order.created_by = request.user
            order.save()
            for form in formset:
                if form.cleaned_data.get('item'):
                    order_item = form.save(commit=False)
                    order_item.order = order
                    order_item.save()
            return redirect('order-list')

        return render(request, 'inventory/create_order.html', {'form': form, 'formset': formset})

class OrderListView(LoginRequiredMixin, View):
    def get(self, request):
        orders = Order.objects.filter(created_by=request.user)
        return render(request, 'inventory/order_list.html', {'orders': orders})

class OrderDetailView(LoginRequiredMixin, View):
    def get(self, request, pk):
        order = get_object_or_404(Order, pk=pk, created_by=request.user)
        return render(request, 'inventory/order_detail.html', {'order': order})

class InventoryLogListView(ListView):
    model = InventoryLog
    template_name = 'inventory/inventory_log_list.html'
    context_object_name = 'logs'
    paginate_by = 20  # Adjust as needed

#@login_required
def bulk_edit_inventory(request):
    category = None  # Initialize category to None
    
    # Check if a category is provided via GET parameters
    if 'category_id' in request.GET:
        try:
            category_id = request.GET.get('category_id')
            category = Category.objects.get(id=category_id)
        except Category.DoesNotExist:
            category = None

    if request.method == 'POST':
        formset = InventoryItemFormSet(request.POST)
        if formset.is_valid():
            user = request.user  # Get the current user
            
            # Iterate through each form in the formset
            for form in formset:
                if form.has_changed():
                    # Save the form
                    form.instance.save()

                    # Record changes in the log
                    for field in form.changed_data:
                        previous_value = form.initial.get(field, None)
                        new_value = getattr(form.instance, field, None)
                        InventoryLog.objects.create(
                            item=form.instance,
                            previous_quantity=previous_value if field == 'quantity' else None,
                            new_quantity=new_value if field == 'quantity' else None,
                            changed_by=user,
                        )

            return redirect('inventory:bulk_edit_inventory')  # Redirect to the same page after saving
    else:
        if category:
            formset = InventoryItemFormSet(queryset=InventoryItem.objects.filter(category=category))
        else:
            formset = InventoryItemFormSet(queryset=InventoryItem.objects.all())

    return render(request, 'inventory/bulk_edit_inventory.html', {'formset': formset})