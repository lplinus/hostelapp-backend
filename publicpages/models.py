# publicpages/models.py

from django.db import models

#Home page model
class HomePage(models.Model):
    hero_title = models.CharField(max_length=255)
    hero_subtitle = models.TextField()

    cta_title = models.CharField(max_length=255)
    cta_subtitle = models.TextField()
    cta_button_text = models.CharField(max_length=100)

    why_title = models.CharField(max_length=255)

    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return "Homepage Content"


class WhyUsItem(models.Model):
    homepage = models.ForeignKey(
        HomePage,
        related_name="why_items",
        on_delete=models.CASCADE
    )
    title = models.CharField(max_length=255)
    description = models.TextField()
    icon = models.CharField(max_length=50, blank=True)
    order = models.PositiveIntegerField(default=0, null=True, blank=True)
    is_active = models.BooleanField(default=True, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)

    def __str__(self):
        return self.title


#About us===================================================

class About(models.Model):
    # Hero Section
    hero_title = models.CharField(max_length=255)
    hero_subtitle = models.TextField()

    # Mission Section
    mission_title = models.CharField(max_length=255)
    mission_description = models.TextField()

    mission_card_title = models.CharField(max_length=255)
    mission_card_description = models.TextField()

    # CTA Section
    cta_title = models.CharField(max_length=255)
    cta_button_text = models.CharField(max_length=100)
    cta_button_url = models.URLField()

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "public_about"
        verbose_name = "About Page"
        verbose_name_plural = "About Page"

    def __str__(self) -> str:
        return "About Page"


#About us stats
class AboutStat(models.Model):
    about = models.ForeignKey(
        About,
        on_delete=models.CASCADE,
        related_name="stats"
    )

    label = models.CharField(max_length=150)
    value = models.CharField(max_length=100)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "public_about_stats"
        ordering = ["order"]

    def __str__(self) -> str:
        return self.label

#About us values
class AboutValue(models.Model):
    about = models.ForeignKey(
        About,
        on_delete=models.CASCADE,
        related_name="values"
    )

    icon_name = models.CharField(max_length=100)
    title = models.CharField(max_length=150)
    description = models.TextField()
    order = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "public_about_values"
        ordering = ["order"]

    def __str__(self) -> str:
        return self.title

#About us team members
class AboutTeamMember(models.Model):
    about = models.ForeignKey(
        About,
        on_delete=models.CASCADE,
        related_name="team_members"
    )

    name = models.CharField(max_length=150)
    role = models.CharField(max_length=150)
    photo = models.ImageField(upload_to="about/team/")
    order = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "public_about_team"
        ordering = ["order"]

    def __str__(self) -> str:
        return self.name




# conatc us page model=====================================================
class Contact(models.Model):
    # Hero Section
    hero_title = models.CharField(max_length=255)
    hero_subtitle = models.TextField()

    # CTA Section
    cta_title = models.CharField(max_length=255)
    cta_button_text = models.CharField(max_length=100)
    cta_button_url = models.URLField()

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "public_contact"
        verbose_name = "Contact Page"
        verbose_name_plural = "Contact Page"

    def __str__(self) -> str:
        return "Contact Page"


# conatc info model
class ContactInfo(models.Model):
    contact = models.ForeignKey(
        Contact,
        on_delete=models.CASCADE,
        related_name="info_items"
    )

    icon_name = models.CharField(max_length=100)  # Mail, Phone, MapPin
    title = models.CharField(max_length=150)
    value = models.CharField(max_length=255)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "public_contact_info"
        ordering = ["order"]

    def __str__(self) -> str:
        return self.title


#faqs models

class ContactFAQ(models.Model):
    contact = models.ForeignKey(
        Contact,
        on_delete=models.CASCADE,
        related_name="faqs"
    )

    question = models.CharField(max_length=255)
    answer = models.TextField()
    order = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "public_contact_faq"
        ordering = ["order"]

    def __str__(self) -> str:
        return self.question



# Contat us form
class ContactMessage(models.Model):
    name = models.CharField(max_length=150)
    email = models.EmailField()
    message = models.TextField()

    is_read = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "public_contact_messages"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.name} - {self.email}"


# Pricing Page Models=============================================================

class Pricing(models.Model):
    # Hero Section
    hero_title = models.CharField(max_length=255)
    hero_subtitle = models.TextField()

    # Comparison Section
    comparison_title = models.CharField(max_length=255)
    comparison_description = models.TextField()

    # CTA Section
    cta_title = models.CharField(max_length=255)
    cta_button_text = models.CharField(max_length=100)
    cta_button_url = models.URLField()

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "public_pricing"
        verbose_name = "Pricing Page"
        verbose_name_plural = "Pricing Page"

    def __str__(self) -> str:
        return "Pricing Page"



# Pricing
class PricingPlan(models.Model):
    pricing = models.ForeignKey(
        Pricing,
        on_delete=models.CASCADE,
        related_name="plans"
    )

    name = models.CharField(max_length=100)
    description = models.CharField(max_length=255)

    price = models.DecimalField(max_digits=10, decimal_places=2)
    currency_symbol = models.CharField(max_length=10, default="₹")
    period = models.CharField(max_length=50, blank=True)  # /month or forever

    is_highlighted = models.BooleanField(default=False)

    order = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "public_pricing_plans"
        ordering = ["order"]

    def __str__(self) -> str:
        return self.name



class PricingFeature(models.Model):
    plan = models.ForeignKey(
        PricingPlan,
        on_delete=models.CASCADE,
        related_name="features"
    )

    feature_text = models.CharField(max_length=255)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "public_pricing_features"
        ordering = ["order"]

    def __str__(self) -> str:
        return self.feature_text


class PricingFAQ(models.Model):
    pricing = models.ForeignKey(
        Pricing,
        on_delete=models.CASCADE,
        related_name="faqs"
    )

    question = models.CharField(max_length=255)
    answer = models.TextField()
    order = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "public_pricing_faq"
        ordering = ["order"]

    def __str__(self) -> str:
        return self.question

