from django.contrib import admin

# Register your models here.
from .models import User,VerificationCode

admin.site.register(User)
admin.site.register(VerificationCode)