from django import forms
from django.forms import modelformset_factory, formset_factory
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from .models import Category, InventoryItem, Order, OrderItem

class UserRegisterForm(UserCreationForm):
	email = forms.EmailField()

	class Meta:
		model = User
		fields = ['username','email','password1','password2']

class InventoryItemForm(forms.ModelForm):
    class Meta:
        model = InventoryItem
        fields = ['quantity']  # Only include quantity, as category will be handled separately
        widgets = {
            'quantity': forms.NumberInput(attrs={'class': 'form-control'}),
        }

# Define the formset with InventoryItemForm and excluding category from being editable
InventoryItemFormSet = modelformset_factory(
    InventoryItem,
    form=InventoryItemForm,
    fields=('quantity',),  # This defines the editable fields in the formset
    extra=0,
)


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name', 'parent']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Adjust parent field to show a hierarchy in a dropdown
        self.fields['parent'].queryset = Category.objects.all()

class CategoryFormBulkEdit(forms.Form):
   categories = forms.ModelMultipleChoiceField(
        queryset=Category.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label='Select Categories to Filter'
    )

class OrderForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = []

class OrderItemForm(forms.ModelForm):
    class Meta:
        model = OrderItem
        fields = ['item', 'quantity_ordered']
        widgets = {
            'quantity_ordered': forms.NumberInput(attrs={'min': 0}),
        }

    def __init__(self, *args, **kwargs):
        items = kwargs.pop('items', InventoryItem.objects.none())  # Default to empty QuerySet if not provided
        super().__init__(*args, **kwargs)
        self.fields['item'].queryset = items

OrderItemFormSet = formset_factory(
    OrderItemForm,
    extra=1
)
