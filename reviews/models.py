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
        related_name="reviews",
        null=True,
        blank=True
    )

    name = models.CharField(max_length=255, blank=True, null=True)
    is_approved = models.BooleanField(default=False)
    published_at = models.DateTimeField(null=True, blank=True)

    rating = models.FloatField(default=5.0)
    hostel_rating = models.IntegerField(default=5)
    food_rating = models.IntegerField(default=5)
    room_rating = models.IntegerField(default=5)
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        # Overall rating is average of hostel, food, and room ratings
        self.rating = round((self.hostel_rating + self.food_rating + self.room_rating) / 3.0, 1)
        super().save(*args, **kwargs)
        self.update_hostel_rating()

    def update_hostel_rating(self):
        from django.db.models import Avg, Count
        hostel = self.hostel
        # Recalculate based on all approved reviews for this hostel
        stats = Review.objects.filter(hostel=hostel, is_approved=True).aggregate(
            avg_rating=Avg('rating'),
            avg_food=Avg('food_rating'),
            avg_room=Avg('room_rating'),
            avg_hostel=Avg('hostel_rating'),
            count=Count('id')
        )
        
        # Update hostel fields
        hostel.rating_avg = round(stats['avg_rating'] or 0, 1)
        hostel.food_rating_avg = round(stats['avg_food'] or 0, 1)
        hostel.room_rating_avg = round(stats['avg_room'] or 0, 1)
        hostel.hostel_rating_avg = round(stats['avg_hostel'] or 0, 1)
        hostel.rating_count = stats['count']
        hostel.save(update_fields=[
            'rating_avg', 
            'food_rating_avg', 
            'room_rating_avg', 
            'hostel_rating_avg', 
            'rating_count'
        ])

    def __str__(self):
        return f"{self.hostel.name} Review ({self.rating}*)"