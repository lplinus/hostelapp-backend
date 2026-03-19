from django.db import models

class SoftDeleteManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=0)

class SoftDeleteModel(models.Model):
    is_deleted = models.IntegerField(default=0, choices=((0, 'Active'), (1, 'Deleted')))

    objects = SoftDeleteManager()
    all_objects = models.Manager()

    class Meta:
        abstract = True

    def delete(self, *args, **kwargs):
        self.is_deleted = 1
        self.save(update_fields=['is_deleted'])

    def hard_delete(self, *args, **kwargs):
        super().delete(*args, **kwargs)


from django.contrib import admin

class SoftDeleteAdmin(admin.ModelAdmin):
    def get_queryset(self, request):
        return self.model.all_objects.all()

    def delete_model(self, request, obj):
        # Allow hard delete from admin if desired, 
        # or stick to soft delete. 
        # Usually, admin delete should be hard delete if the user said "unless deleting it manually".
        obj.hard_delete()
