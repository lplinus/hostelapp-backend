# Seed script: Create location data + 20 dummy hostels.

from django.utils.text import slugify
from accounts.models import User
from locations.models import Country, State, City, Area
from hostels.models import Hostel
from amenities.models import Amenity
from datetime import time
from decimal import Decimal
import random

# 1. Ensure an owner user exists
owner, _ = User.objects.get_or_create(
    username="hosteladmin",
    defaults={
        "email": "admin@staynest.com",
        "role": "hostel_owner",
        "is_verified": True,
    },
)
if not owner.has_usable_password():
    owner.set_password("admin1234")
    owner.save()

# 2. Create locations
country, _ = Country.objects.get_or_create(
    slug="india",
    defaults={"name": "India", "iso_code": "IN"},
)

states_data = [
    ("Telangana", "telangana"),
    ("Karnataka", "karnataka"),
    ("Maharashtra", "maharashtra"),
    ("Tamil Nadu", "tamil-nadu"),
]
states = {}
for name, slug in states_data:
    s, _ = State.objects.get_or_create(
        slug=slug, defaults={"name": name, "country": country}
    )
    states[slug] = s

cities_data = [
    ("Hyderabad", "hyderabad", "telangana", 17.385044, 78.486671),
    ("Bangalore", "bangalore", "karnataka", 12.971599, 77.594566),
    ("Mumbai", "mumbai", "maharashtra", 19.075984, 72.877656),
    ("Chennai", "chennai", "tamil-nadu", 13.082680, 80.270721),
    ("Pune", "pune", "maharashtra", 18.520430, 73.856743),
]
cities = {}
for name, slug, state_slug, lat, lng in cities_data:
    c, _ = City.objects.get_or_create(
        slug=slug,
        defaults={
            "name": name,
            "state": states[state_slug],
            "latitude": Decimal(str(lat)),
            "longitude": Decimal(str(lng)),
        },
    )
    cities[slug] = c

areas_data = [
    ("Madhapur", "madhapur", "hyderabad"),
    ("Gachibowli", "gachibowli", "hyderabad"),
    ("Ameerpet", "ameerpet", "hyderabad"),
    ("Kukatpally", "kukatpally", "hyderabad"),
    ("Koramangala", "koramangala", "bangalore"),
    ("Indiranagar", "indiranagar", "bangalore"),
    ("Andheri", "andheri", "mumbai"),
    ("Bandra", "bandra", "mumbai"),
    ("T Nagar", "t-nagar", "chennai"),
    ("Adyar", "adyar", "chennai"),
    ("Kothrud", "kothrud", "pune"),
    ("Viman Nagar", "viman-nagar", "pune"),
]
areas = {}
for name, slug, city_slug in areas_data:
    a, _ = Area.objects.get_or_create(
        slug=slug,
        city=cities[city_slug],
        defaults={
            "name": name,
            "latitude": cities[city_slug].latitude,
            "longitude": cities[city_slug].longitude,
        },
    )
    areas[slug] = a

# 3. Create amenities
amenity_names = [
    "Free Wi-Fi",
    "AC",
    "Hot Water",
    "Laundry",
    "CCTV",
    "Parking",
    "Kitchen",
    "Gym",
    "Power Backup",
    "Study Room",
]
amenities_list = []
for name in amenity_names:
    am, _ = Amenity.objects.get_or_create(name=name)
    amenities_list.append(am)

# 4. Create 20 hostels
hostels_data = [
    # (name, city_slug, area_slug, price, is_featured)
    ("StayNest Premium Hostel", "hyderabad", "madhapur", 5500, True),
    ("Urban Nest Co-Living", "hyderabad", "gachibowli", 4800, True),
    ("Campus Corner Hostel", "hyderabad", "ameerpet", 3500, False),
    ("Skyline Student Stay", "hyderabad", "kukatpally", 4000, False),
    ("NestAway Hyderabad", "hyderabad", "madhapur", 6000, True),
    ("Koramangala Comfort Hostel", "bangalore", "koramangala", 7000, True),
    ("IndiHub Co-Living", "bangalore", "indiranagar", 6500, True),
    ("BLR Backpackers Hostel", "bangalore", "koramangala", 3800, False),
    ("Tech Park Residency", "bangalore", "indiranagar", 5200, False),
    ("Mumbai Central Hostel", "mumbai", "andheri", 5500, True),
    ("Bandra Beach Hostel", "mumbai", "bandra", 7500, True),
    ("Gateway Student Stay", "mumbai", "andheri", 4200, False),
    ("SoBo Nest Hostel", "mumbai", "bandra", 6800, False),
    ("Marina Bay Hostel", "chennai", "t-nagar", 3200, False),
    ("Adyar Student Nest", "chennai", "adyar", 3800, True),
    ("Chennai Central Stay", "chennai", "t-nagar", 4500, False),
    ("IIT Gate Hostel", "chennai", "adyar", 4000, False),
    ("Pune Hills Hostel", "pune", "kothrud", 3500, False),
    ("Viman Nagar Living", "pune", "viman-nagar", 4800, True),
    ("Pune Study Hub", "pune", "kothrud", 4200, False),
]

descriptions = [
    "A modern, fully-furnished hostel designed for students and working professionals. Located in the heart of the city with excellent connectivity to major IT parks and universities.",
    "Experience comfortable co-living with premium amenities. Our hostel offers spacious rooms, nutritious meals, and a vibrant community atmosphere.",
    "Affordable yet premium student accommodation with 24/7 security, high-speed internet, and a dedicated study zone. Perfect for focused students.",
    "A home away from home. We provide clean, well-maintained rooms with all essential amenities to make your stay comfortable and productive.",
    "Stay in the most happening neighborhood! Our hostel combines urban convenience with homely comfort. Great food, great vibes, great people.",
]

for i, (name, city_slug, area_slug, price, featured) in enumerate(hostels_data):
    slug = slugify(name)
    hostel, created = Hostel.objects.update_or_create(
        slug=slug,
        defaults={
            "name": name,
            "owner": owner,
            "city": cities[city_slug],
            "area": areas[area_slug],
            "description": descriptions[i % len(descriptions)],
            "short_description": f"Best hostel experience in {areas[area_slug].name}, {cities[city_slug].name}.",
            "price": Decimal(str(price)),
            "address": f"{random.randint(1, 500)}, {areas[area_slug].name} Main Road, {cities[city_slug].name}",
            "postal_code": str(random.randint(400001, 600100)),
            "latitude": (cities[city_slug].latitude or Decimal("17.385044"))
            + Decimal(str(round(random.uniform(-0.02, 0.02), 6))),
            "longitude": (cities[city_slug].longitude or Decimal("78.486671"))
            + Decimal(str(round(random.uniform(-0.02, 0.02), 6))),
            "check_in_time": time(14, 0),
            "check_out_time": time(11, 0),
            "rating_avg": round(random.uniform(3.5, 4.9), 1),
            "rating_count": random.randint(10, 250),
            "is_active": True,
            "is_featured": featured,
        },
    )
    # Assign random 3-6 amenities
    hostel.amenities.set(random.sample(amenities_list, random.randint(3, 6)))

    status = "Created" if created else "Updated"
    print(f"  {status}: {name} ({'* Featured' if featured else 'Regular'})")

print(f"Done! {Hostel.objects.count()} hostels in database.")
print(f"Featured: {Hostel.objects.filter(is_featured=True).count()}")
print(f"Cities: {City.objects.count()}")
print(f"Areas: {Area.objects.count()}")
print(f"Amenities: {Amenity.objects.count()}")
