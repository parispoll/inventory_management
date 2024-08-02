from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import InventoryItem, AuditLog
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
