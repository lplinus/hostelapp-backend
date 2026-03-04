from django.contrib import admin

# Register your models here.
from .models import Country, State, City, Area

admin.site.register(Country)
admin.site.register(State)
admin.site.register(City)
admin.site.register(Area)

# admin.site.register(Location)

