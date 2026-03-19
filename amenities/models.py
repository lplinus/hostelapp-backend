from django.db import models
from Hbackend.base_models import SoftDeleteModel


class Amenity(SoftDeleteModel):
    name = models.CharField(max_length=100)
    icon = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return self.name