from django.db import models
from django.contrib.auth.models import User

class InventoryItem(models.Model):
    name = models.CharField(max_length=200)
    quantity = models.IntegerField()
    category = models.ForeignKey('Category', on_delete=models.SET_NULL, blank=True, null=True)
    date_created = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    def __str__(self):
        return self.name

class InventoryLog(models.Model):
   item = models.ForeignKey(InventoryItem, on_delete=models.CASCADE)
   previous_quantity = models.PositiveIntegerField(null=True, blank=True)
   new_quantity = models.PositiveIntegerField(null=True, blank=True)
   changed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
   timestamp = models.DateTimeField(auto_now_add=True)
    
   def __str__(self):
        return f"{self.item.name} changed from {self.previous_quantity} to {self.new_quantity} on {self.timestamp}"

class Category(models.Model):
    name = models.CharField(max_length=100)
    parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.CASCADE, related_name='subcategories')

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Category"
        verbose_name_plural = "Categories"

class AuditLog(models.Model):
    ACTION_CHOICES = [
        ('CREATE', 'Created'),
        ('UPDATE', 'Updated'),
        ('DELETE', 'Deleted'),
    ]

    action = models.CharField(max_length=10, choices=ACTION_CHOICES)
    item = models.ForeignKey(InventoryItem, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    changes = models.TextField()  # JSON or text field to describe changes

    def __str__(self):
        return f"{self.action} - {self.item.name} by {self.user.username if self.user else 'Unknown'}"

class Department(models.Model):
    name = models.CharField(max_length=100)
    accessible_categories = models.ManyToManyField('Category', related_name='departments')
    
    def __str__(self):
        return self.name

class Order(models.Model):
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='orders')
    items = models.ManyToManyField(InventoryItem, through='OrderItem')
    date_created = models.DateTimeField(auto_now_add=True)
    confirmed = models.BooleanField(default=False)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)

    def __str__(self):
        return f"Order {self.id} by {self.department.name}"



class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE)
    item = models.ForeignKey(InventoryItem, on_delete=models.CASCADE)
    quantity_ordered = models.PositiveIntegerField()

    def __str__(self):
        return f"{self.quantity_ordered} x {self.item.name}"

