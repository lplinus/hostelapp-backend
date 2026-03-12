from django.db import models


# Terms and Conditions

class TermsAndConditions(models.Model):
    title = models.CharField(max_length=255)
    content = models.TextField()
    effective_date = models.DateField()
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Terms and Conditions"
        verbose_name_plural = "Terms and Conditions"

    def __str__(self):
        return self.title



# Privacy Policy

class PrivacyPolicy(models.Model):
    title = models.CharField(max_length=255)
    content = models.TextField()
    effective_date = models.DateField()
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Privacy Policy"
        verbose_name_plural = "Privacy Policies"

    def __str__(self):
        return self.title