from django.db import models
from Hbackend.base_models import SoftDeleteModel
from accounts.models import User
from hostels.models import Hostel
from hotels.models import Hotel
from vacanationrentals.models import VacationRental


class Review(SoftDeleteModel):
    """
    Review model for Hostels.
    Can be anchored to a specific verified hostel Booking.
    """
    booking = models.OneToOneField(
        "bookings.Booking",
        on_delete=models.CASCADE,
        related_name="review",
        null=True,
        blank=True,
        help_text="Anchored verified booking",
    )

    hostel = models.ForeignKey(
        Hostel,
        on_delete=models.CASCADE,
        related_name="reviews",
    )

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="reviews",
        null=True,
        blank=True,
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

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Hostel Review"
        verbose_name_plural = "Hostel Reviews"

    def save(self, *args, **kwargs):
        # Overall rating is calculated based on food and room ratings
        self.rating = round((self.food_rating + self.room_rating) / 2.0, 1)
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


class HotelReview(SoftDeleteModel):
    """
    Dedicated review and rating model for Hotels.
    Anchored to a verified HotelBooking.
    Evaluates criteria: cleanliness, comfort, service, and location.
    """
    booking = models.OneToOneField(
        "hotels.HotelBooking",
        on_delete=models.CASCADE,
        related_name="review",
        null=True,
        blank=True,
        help_text="Anchored verified booking",
    )

    hotel = models.ForeignKey(
        Hotel,
        on_delete=models.CASCADE,
        related_name="reviews",
    )

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="hotel_reviews",
        null=True,
        blank=True,
    )

    name = models.CharField(max_length=255, blank=True, null=True)
    is_approved = models.BooleanField(default=False)
    published_at = models.DateTimeField(null=True, blank=True)

    rating = models.FloatField(default=5.0)
    cleanliness_rating = models.IntegerField(default=5)
    comfort_rating = models.IntegerField(default=5)
    service_rating = models.IntegerField(default=5)
    location_rating = models.IntegerField(default=5)
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Hotel Review"
        verbose_name_plural = "Hotel Reviews"

    def save(self, *args, **kwargs):
        # Calculate overall rating from standard hotel categories
        total = self.cleanliness_rating + self.comfort_rating + self.service_rating + self.location_rating
        self.rating = round(total / 4.0, 1)
        super().save(*args, **kwargs)
        self.update_hotel_rating()

    def update_hotel_rating(self):
        from django.db.models import Avg, Count
        hotel = self.hotel
        stats = HotelReview.objects.filter(hotel=hotel, is_approved=True).aggregate(
            avg_rating=Avg('rating'),
            count=Count('id')
        )
        hotel.rating_avg = round(stats['avg_rating'] or 0.0, 1)
        hotel.rating_count = stats['count']
        hotel.save(update_fields=['rating_avg', 'rating_count'])

    def __str__(self):
        return f"{self.hotel.name} Review ({self.rating}★)"


class VacationRentalReview(SoftDeleteModel):
    """
    Dedicated review and rating model for Vacation Rentals.
    Anchored to a verified VacationRentalBooking.
    Evaluates standard Airbnb-style vacation rental criteria:
    cleanliness, accuracy, checkin, communication, location, and value.
    """
    booking = models.OneToOneField(
        "vacanationrentals.VacationRentalBooking",
        on_delete=models.CASCADE,
        related_name="review",
        null=True,
        blank=True,
        help_text="Anchored verified booking",
    )

    rental = models.ForeignKey(
        VacationRental,
        on_delete=models.CASCADE,
        related_name="reviews",
    )

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="vacation_rental_reviews",
        null=True,
        blank=True,
    )

    name = models.CharField(max_length=255, blank=True, null=True)
    is_approved = models.BooleanField(default=False)
    published_at = models.DateTimeField(null=True, blank=True)

    rating = models.FloatField(default=5.0)
    cleanliness_rating = models.IntegerField(default=5)
    accuracy_rating = models.IntegerField(default=5)
    checkin_rating = models.IntegerField(default=5)
    communication_rating = models.IntegerField(default=5)
    location_rating = models.IntegerField(default=5)
    value_rating = models.IntegerField(default=5)
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Vacation Rental Review"
        verbose_name_plural = "Vacation Rental Reviews"

    def save(self, *args, **kwargs):
        # Calculate overall rating from standard vacation rental categories
        total = (
            self.cleanliness_rating
            + self.accuracy_rating
            + self.checkin_rating
            + self.communication_rating
            + self.location_rating
            + self.value_rating
        )
        self.rating = round(total / 6.0, 1)
        super().save(*args, **kwargs)
        self.update_rental_rating()

    def update_rental_rating(self):
        from django.db.models import Avg, Count
        rental = self.rental
        stats = VacationRentalReview.objects.filter(rental=rental, is_approved=True).aggregate(
            avg_rating=Avg('rating'),
            count=Count('id')
        )
        rental.rating_avg = round(stats['avg_rating'] or 0.0, 1)
        rental.rating_count = stats['count']
        rental.save(update_fields=['rating_avg', 'rating_count'])

    def __str__(self):
        return f"{self.rental.title} Review ({self.rating}★)"
