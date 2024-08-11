from django import forms
from django.forms import modelformset_factory
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from .models import Category, InventoryItem, Order, OrderItem

class UserRegisterForm(UserCreationForm):
	email = forms.EmailField()

	class Meta:
		model = User
		fields = ['username','email','password1','password2']

class InventoryItemForm(forms.ModelForm):
	category = forms.ModelChoiceField(queryset=Category.objects.all(), initial=0)
	class Meta:
		model = InventoryItem
		fields = ['name','quantity','category']

class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name', 'parent']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Adjust parent field to show a hierarchy in a dropdown
        self.fields['parent'].queryset = Category.objects.all()

class OrderForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = []

class OrderItemForm(forms.ModelForm):
    class Meta:
        model = OrderItem
        fields = ['item', 'quantity']

    def __init__(self, *args, **kwargs):
        items = kwargs.pop('items', None)
        super().__init__(*args, **kwargs)
        if items:
            self.fields['item'].queryset = items

OrderItemFormSet = forms.inlineformset_factory(Order, OrderItem, form=OrderItemForm, extra=1)

class InventoryItemForm(forms.ModelForm):
    class Meta:
        model = InventoryItem
        fields = ['name', 'category', 'quantity']  # Include any other fields you want to edit

InventoryItemFormSet = modelformset_factory(InventoryItem, form=InventoryItemForm, extra=0)