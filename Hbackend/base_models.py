"""
Common base models and managers for the entire project.
Includes support for soft-deletion and custom admin classes.
"""
from django.db import models

class SoftDeleteManager(models.Manager):
    """
    Custom manager that filters out 'deleted' records by default.
    """
    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=0)

class SoftDeleteModel(models.Model):
    """
    An abstract base class that provides soft-lookup/soft-deletion capabilities.
    Instead of removing rows from the database, it marks them as deleted.
    """
    is_deleted = models.IntegerField(default=0, choices=((0, 'Active'), (1, 'Deleted')))

    objects = SoftDeleteManager()
    all_objects = models.Manager()

    class Meta:
        abstract = True

    def delete(self, *args, **kwargs):
        """
        Overrides the default delete method to perform a soft delete.
        Sets 'is_deleted' flag to 1.
        """
        self.is_deleted = 1
        self.save(update_fields=['is_deleted'])

    def hard_delete(self, *args, **kwargs):
        """
        Performs a real database deletion.
        """
        super().delete(*args, **kwargs)


from django.contrib import admin

class SoftDeleteAdmin(admin.ModelAdmin):
    """
    Custom admin class for SoftDeleteModel.
    Ensures that 'deleted' items can still be seen and managed in the Django Admin.
    """
    def get_queryset(self, request):
        return self.model.all_objects.all()

    def delete_model(self, request, obj):
        """
        Perform soft delete instead of hard delete when 'Delete' is clicked in the admin.
        """
        obj.delete()
