from django.db import models
from Hbackend.base_models import SoftDeleteModel
from accounts.models import User
from hostels.models import Hostel


class Review(SoftDeleteModel):
    hostel = models.ForeignKey(
        Hostel,
        on_delete=models.CASCADE,
        related_name="reviews"
    )

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="reviews"
    )

    rating = models.IntegerField()
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.hostel.name} Review"