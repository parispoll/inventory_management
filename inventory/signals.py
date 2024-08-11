from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver
from .models import InventoryItem, AuditLog, InventoryLog
import json

@receiver(post_save, sender=InventoryItem)
def log_inventory_item_change(sender, instance, created, **kwargs):
    if created:
        action = 'CREATE'
    else:
        action = 'UPDATE'
    
    changes = {
        'name': instance.name,
        'quantity': instance.quantity,
        'category': instance.category.name if instance.category else None
    }
    
    AuditLog.objects.create(
        action=action,
        item=instance,
        user=instance.user,
        changes=json.dumps(changes)
    )

@receiver(post_delete, sender=InventoryItem)
def log_inventory_item_deletion(sender, instance, **kwargs):
    changes = {
        'name': instance.name,
        'quantity': instance.quantity,
        'category': instance.category.name if instance.category else None
    }

    AuditLog.objects.create(
        action='DELETE',
        item=instance,
        user=instance.user,
        changes=json.dumps(changes)
    )

@receiver(pre_save, sender=InventoryItem)
def log_inventory_change(sender, instance, **kwargs):
    if instance.pk:
        previous_instance = InventoryItem.objects.get(pk=instance.pk)
        if previous_instance.quantity != instance.quantity:
            InventoryLog.objects.create(
                item=instance,
                previous_quantity=previous_instance.quantity,
                new_quantity=instance.quantity,
                changed_by=getattr(instance, '_changed_by', None)
            )