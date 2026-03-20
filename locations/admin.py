from django.contrib import admin

# Register your models here.
from Hbackend.base_models import SoftDeleteAdmin
from .models import Country, State, City, Area

@admin.register(Country)
class CountryAdmin(SoftDeleteAdmin):
    list_display = ("name", "iso_code", "is_deleted")
    list_filter = ("is_deleted",)

@admin.register(State)
class StateAdmin(SoftDeleteAdmin):
    list_display = ("name", "country", "is_deleted")
    list_filter = ("country", "is_deleted")

@admin.register(City)
class CityAdmin(SoftDeleteAdmin):
    list_display = ("name", "state", "is_deleted")
    list_filter = ("state", "is_deleted")

@admin.register(Area)
class AreaAdmin(SoftDeleteAdmin):
    list_display = ("name", "city", "is_deleted")
    list_filter = ("city", "is_deleted")

# admin.site.register(Location)

