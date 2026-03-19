# from django.db import models
# from Hbackend.utils import process_image_fields


# class Country(models.Model):
#     name = models.CharField(max_length=100)
#     iso_code = models.CharField(max_length=10)
#     slug = models.SlugField(unique=True)

#     def __str__(self):
#         return self.name


# class State(models.Model):
#     name = models.CharField(max_length=100)
#     slug = models.SlugField(unique=True)
#     country = models.ForeignKey(
#         Country,
#         on_delete=models.CASCADE,
#         related_name="states"
#     )

#     def __str__(self):
#         return self.name


# class City(models.Model):
#     name = models.CharField(max_length=100)
#     slug = models.SlugField(unique=True)
#     city_image = models.ImageField(upload_to='cities', null=True, blank=True)
#     state = models.ForeignKey(
#         State,
#         on_delete=models.CASCADE,
#         related_name="cities"
#     )
#     latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
#     longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
#     def save(self, *args, **kwargs):
#         # Convert all image fields to WebP on save
#         process_image_fields(
#             self,
#             ["city_image"],
#         )
#         super().save(*args, **kwargs)

#     def __str__(self):
#         return self.name


# class Area(models.Model):
#     name = models.CharField(max_length=150)
#     slug = models.SlugField()

#     city = models.ForeignKey(
#         City,
#         on_delete=models.CASCADE,
#         related_name="areas"
#     )

#     latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
#     longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)

#     class Meta:
#         unique_together = ("slug", "city")

#     def __str__(self):
#         return f"{self.name}, {self.city.name}"



from django.db import models
from django.utils.text import slugify
from Hbackend.utils import process_image_fields
from Hbackend.base_models import SoftDeleteModel


def generate_unique_slug(instance, field_name: str, queryset=None):
    base_slug = slugify(getattr(instance, field_name))
    slug = base_slug
    counter = 1

    if queryset is None:
        queryset = instance.__class__.objects.all()

    while queryset.filter(slug=slug).exists():
        slug = f"{base_slug}-{counter}"
        counter += 1

    return slug


class Country(models.Model):
    name = models.CharField(max_length=100)
    iso_code = models.CharField(max_length=10)
    slug = models.SlugField(unique=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["slug"]),
        ]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = generate_unique_slug(self, "name")
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class State(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True, blank=True)
    country = models.ForeignKey(
        Country,
        on_delete=models.CASCADE,
        related_name="states"
    )

    class Meta:
        indexes = [
            models.Index(fields=["slug"]),
        ]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = generate_unique_slug(self, "name")
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class City(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True, blank=True)
    city_image = models.ImageField(upload_to='cities', null=True, blank=True)
    state = models.ForeignKey(
        State,
        on_delete=models.CASCADE,
        related_name="cities"
    )
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["slug"]),
        ]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = generate_unique_slug(self, "name")

        from Hbackend.utils import process_image_fields, delete_old_image_files
        delete_old_image_files(self, ["city_image"])
        # Convert image fields to WebP
        process_image_fields(
            self,
            ["city_image"],
        )

        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Area(models.Model):
    name = models.CharField(max_length=150)
    slug = models.SlugField(blank=True)

    city = models.ForeignKey(
        City,
        on_delete=models.CASCADE,
        related_name="areas"
    )

    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)

    class Meta:
        unique_together = ("slug", "city")
        indexes = [
            models.Index(fields=["slug", "city"]),
        ]

    def save(self, *args, **kwargs):
        if not self.slug:
            queryset = Area.objects.filter(city=self.city)
            self.slug = generate_unique_slug(self, "name", queryset=queryset)

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name}, {self.city.name}"