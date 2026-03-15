# publicpages/models.py

from django.db import models


# Home page model
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
        HomePage, related_name="why_items", on_delete=models.CASCADE
    )
    title = models.CharField(max_length=255)
    description = models.TextField()
    icon = models.CharField(max_length=50, blank=True)
    order = models.PositiveIntegerField(default=0, null=True, blank=True)
    is_active = models.BooleanField(default=True, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)

    def __str__(self):
        return self.title


# About us===================================================


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


# About us stats
class AboutStat(models.Model):
    about = models.ForeignKey(About, on_delete=models.CASCADE, related_name="stats")

    label = models.CharField(max_length=150)
    value = models.CharField(max_length=100)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "public_about_stats"
        ordering = ["order"]

    def __str__(self) -> str:
        return self.label


# About us values
class AboutValue(models.Model):
    about = models.ForeignKey(About, on_delete=models.CASCADE, related_name="values")

    icon_name = models.CharField(max_length=100)
    title = models.CharField(max_length=150)
    description = models.TextField()
    order = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "public_about_values"
        ordering = ["order"]

    def __str__(self) -> str:
        return self.title


# About us team members
class AboutTeamMember(models.Model):
    about = models.ForeignKey(
        About, on_delete=models.CASCADE, related_name="team_members"
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
        Contact, on_delete=models.CASCADE, related_name="info_items"
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


# faqs models


class ContactFAQ(models.Model):
    contact = models.ForeignKey(Contact, on_delete=models.CASCADE, related_name="faqs")

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
    email = models.EmailField(blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    message = models.TextField()

    # New fields for "Request Callback" and "Reply"
    hostel = models.ForeignKey(
        "hostels.Hostel",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="inquiries",
    )

    reply = models.TextField(blank=True, null=True)
    is_replied = models.BooleanField(default=False)
    replied_at = models.DateTimeField(null=True, blank=True)

    is_read = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "public_contact_messages"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.name} - {self.email or self.phone}"


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
    pricing = models.ForeignKey(Pricing, on_delete=models.CASCADE, related_name="plans")

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
        PricingPlan, on_delete=models.CASCADE, related_name="features"
    )

    feature_text = models.CharField(max_length=255)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "public_pricing_features"
        ordering = ["order"]

    def __str__(self) -> str:
        return self.feature_text


class PricingFAQ(models.Model):
    pricing = models.ForeignKey(Pricing, on_delete=models.CASCADE, related_name="faqs")

    question = models.CharField(max_length=255)
    answer = models.TextField()
    order = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "public_pricing_faq"
        ordering = ["order"]

    def __str__(self) -> str:
        return self.question


# Landing Page Models =============================================================


class LandingPage(models.Model):
    # Hero Section
    hero_badge = models.CharField(
        max_length=255, default="India's Most Trusted Student Hub"
    )
    hero_title_main = models.CharField(max_length=255)
    hero_title_italic = models.CharField(max_length=255)
    hero_title_footer = models.CharField(max_length=255)
    hero_description = models.TextField()
    hero_primary_cta_text = models.CharField(max_length=100, default="Explore Hostels")
    hero_primary_cta_url = models.CharField(max_length=255, default="/home")
    hero_secondary_cta_text = models.CharField(max_length=100, default="Our Standards")
    hero_secondary_cta_url = models.CharField(max_length=255, default="#how")

    # Cities Section
    cities_eyebrow = models.CharField(max_length=255, default="Discover Your Hub")
    cities_title_main = models.CharField(max_length=255, default="Most Popular")
    cities_title_italic = models.CharField(max_length=255, default="Destinations")

    # Features Section
    features_eyebrow = models.CharField(max_length=255, default="The LiveHub Advantage")
    features_title_main = models.CharField(
        max_length=255, default="Everything You Need,"
    )
    features_title_italic = models.CharField(
        max_length=255, default="Nothing You Don't."
    )
    features_subtitle = models.TextField()

    # How It Works Section
    how_eyebrow = models.CharField(max_length=255, default="The LiveHub Journey")
    how_title_main = models.CharField(max_length=255, default="Booking Made")
    how_title_italic = models.CharField(max_length=255, default="Simple.")
    how_subtitle = models.TextField()

    # Testimonials Section
    testimonials_eyebrow = models.CharField(max_length=255, default="Real Experiences")
    testimonials_title_main = models.CharField(max_length=255, default="Trusted by")
    testimonials_title_italic = models.CharField(max_length=255, default="Thousands")

    # CTA Section (Bottom)
    cta_bottom_eyebrow = models.CharField(max_length=255, default="Start your journey")
    cta_bottom_title_main = models.CharField(max_length=255, default="Ready for your")
    cta_bottom_title_italic = models.CharField(max_length=255, default="next chapter?")
    cta_bottom_subtitle = models.TextField()
    cta_bottom_button_text = models.CharField(max_length=100, default="Start Exploring")
    cta_bottom_button_url = models.CharField(max_length=255, default="/home")

    is_active = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "public_landing_page"
        verbose_name = "Landing Page"
        verbose_name_plural = "Landing Page"

    def __str__(self):
        return "Landing Page Content"


class LandingStat(models.Model):
    landing_page = models.ForeignKey(
        LandingPage, related_name="stats", on_delete=models.CASCADE
    )
    number = models.CharField(max_length=50)
    label = models.CharField(max_length=100)
    icon_name = models.CharField(max_length=50)
    color_gradient = models.CharField(max_length=100)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "public_landing_stats"
        ordering = ["order"]

    def __str__(self):
        return f"{self.number} - {self.label}"


class LandingCityItem(models.Model):
    landing_page = models.ForeignKey(
        LandingPage, related_name="cities", on_delete=models.CASCADE
    )
    city_name = models.CharField(max_length=100)
    count_text = models.CharField(max_length=100)
    image = models.ImageField(upload_to="landing/cities/", null=True, blank=True)
    span_large = models.BooleanField(default=False)
    gradient = models.CharField(max_length=255)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "public_landing_cities"
        ordering = ["order"]

    def __str__(self):
        return self.city_name


class LandingFeatureItem(models.Model):
    landing_page = models.ForeignKey(
        LandingPage, related_name="features", on_delete=models.CASCADE
    )
    icon_name = models.CharField(max_length=50)
    title = models.CharField(max_length=255)
    text = models.TextField()
    order = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "public_landing_features"
        ordering = ["order"]

    def __str__(self):
        return self.title


class LandingStepItem(models.Model):
    landing_page = models.ForeignKey(
        LandingPage, related_name="steps", on_delete=models.CASCADE
    )
    step_number = models.CharField(max_length=10)
    icon_name = models.CharField(max_length=50)
    title = models.CharField(max_length=255)
    text = models.TextField()
    order = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "public_landing_steps"
        ordering = ["order"]

    def __str__(self):
        return f"{self.step_number} - {self.title}"


class LandingTestimonialItem(models.Model):
    landing_page = models.ForeignKey(
        LandingPage, related_name="testimonials", on_delete=models.CASCADE
    )
    text = models.TextField()
    name = models.CharField(max_length=255)
    role = models.CharField(max_length=255)
    initial = models.CharField(max_length=10)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "public_landing_testimonials"
        ordering = ["order"]

    def __str__(self):
        return self.name
