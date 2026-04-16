from hostels.models import Hostel
from rooms.models import RoomType
from amenities.models import Amenity
from locations.models import City
import json

def format_price(val):
    try:
        if not val: return "0"
        return "{:,.0f}".format(float(val))
    except:
        return "0"

def get_hostel_knowledge_base():
    """
    Fetches all active hostels and their full details to provide rich context to the AI.
    """
    hostels = Hostel.objects.filter(
        is_active=True, is_approved=True
    ).select_related("city", "area").prefetch_related(
        "room_types", "amenities", "landmarks", "extra_charges"
    )

    # Build city summary
    cities = City.objects.all()
    city_list = [c.name for c in cities]

    kb_parts = []
    kb_parts.append(f"CITIES WE OPERATE IN: {', '.join(city_list)}")
    kb_parts.append(f"TOTAL HOSTELS: {hostels.count()}")
    kb_parts.append("---")

    try:
        for hostel in hostels:
            # Room details
            rooms = []
            for r in hostel.room_types.filter(is_available=True):
                price_str = format_price(r.base_price)
                rooms.append(
                    f"  - {r.get_room_category_display()} / {r.get_sharing_type_display()}: ₹{price_str}/month"
                )

            # Amenities
            amenities = [a.name for a in hostel.amenities.all()]

            # Landmarks
            landmarks = [f"{l.name} ({l.distance})" for l in hostel.landmarks.all()]

            # Extra charges
            charges = []
            for c in hostel.extra_charges.all():
                amt_str = format_price(c.amount)
                charges.append(
                    f"  - {c.get_charge_type_display()}: ₹{amt_str} ({c.description or 'N/A'})"
                )

            # Discount info
            discount_info = ""
            if hostel.is_discounted and hostel.discount_percentage:
                disc_price = format_price(hostel.discounted_price)
                discount_info = f"  DISCOUNT: {hostel.discount_percentage}% OFF! Discounted price: ₹{disc_price}/month"

            # Rating info
            rating_info = ""
            if hostel.rating_avg > 0:
                rating_info = f"  Rating: {hostel.rating_avg}/5 ({hostel.rating_count} reviews)"

            entry = f"""
HOSTEL: {hostel.name}
  Type: {hostel.get_hostel_type_display()}
  City: {hostel.city.name if hostel.city else 'N/A'}, Area: {hostel.area.name if hostel.area else 'N/A'}
  Starting Price: ₹{format_price(hostel.price)}/month
  Description: {hostel.short_description or hostel.description[:200] if hostel.description else 'N/A'}
  Check-in: {hostel.check_in_time}, Check-out: {hostel.check_out_time}
  Verified: {'Yes' if hostel.is_verified else 'No'}
{discount_info}
{rating_info}
  Amenities: {', '.join(amenities) if amenities else 'N/A'}
  Room Types:
{chr(10).join(rooms) if rooms else '  - No rooms listed'}
  Nearby Landmarks: {', '.join(landmarks) if landmarks else 'N/A'}
  Extra Charges:
{chr(10).join(charges) if charges else '  - None'}
---"""
            kb_parts.append(entry)

    except Exception as e:
        print(f"Error building knowledge base: {e}")
        return "No hostel data available at this time."

    return "\n".join(kb_parts)
