from django.shortcuts import render, redirect
from django.urls import reverse_lazy
from django.views.generic import TemplateView, View, CreateView, UpdateView, DeleteView
from django.contrib.auth import authenticate, login
from django.contrib.auth.mixins import LoginRequiredMixin
from .forms import UserRegisterForm, InventoryItemForm
from .models import InventoryItem, Category
from inventory_management.settings import LOW_QUANTITY
from django.contrib import messages
from django.db import models  # Import models her

class Index(TemplateView):
	template_name= 'inventory/index.html'

class Dashboard(LoginRequiredMixin, View):
	def get(self,request):
		items = InventoryItem.objects.filter(user=self.request.user.id).order_by('id')

		low_inventory = InventoryItem.objects.filter(user=self.request.user.id,quantity__lte=LOW_QUANTITY)
		low_inventory_ids = []

		if low_inventory.count()>0:
			if low_inventory.count()>1:
				messages.error(request, f'{low_inventory.count()} items have low inventory')
			else:
				messages.error(request, f'{low_inventory.count()} item has low inventory')

			low_inventory_ids = InventoryItem.objects.filter(user=self.request.user.id,quantity__lte=LOW_QUANTITY).values_list('id', flat=True)

		return render(request, 'inventory/dashboard.html', {'items': items, 'low_inventory_ids': low_inventory_ids})

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

class EditItem(LoginRequiredMixin, UpdateView):
	model = InventoryItem
	form_class = InventoryItemForm
	template_name = 'inventory/item_form.html'
	success_url = reverse_lazy('dashboard')

class DeleteItem(LoginRequiredMixin, DeleteView):
	model = InventoryItem
	template_name = 'inventory/delete_item.html'
	success_url = reverse_lazy('dashboard')
	context_object_name = 'item'

class InventorySummaryReport(LoginRequiredMixin, View):
    def get(self, request):
        total_items = InventoryItem.objects.filter(user=self.request.user).count()
        total_quantity = InventoryItem.objects.filter(user=self.request.user).aggregate(total_quantity=models.Sum('quantity'))['total_quantity'] or 0
        categories = Category.objects.all()
        category_counts = {category.name: InventoryItem.objects.filter(user=self.request.user, category=category).count() for category in categories}

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