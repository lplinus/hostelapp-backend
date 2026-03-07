import os
import django
import sys

sys.path.append(
    r"c:\Users\lakka\OneDrive\Desktop\techsproutai\django-nextjs\App\Hbackend"
)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "Hbackend.settings")
django.setup()

from rooms.serializers import RoomTypeSerializer
from rooms.models import RoomType, Hostel

print(f"Total RoomTypes: {RoomType.objects.count()}")

# Try to validate update
rt = RoomType.objects.first()
if rt:
    print(f"Testing update on RoomType {rt.id}")
    data = {
        "hostel": rt.hostel.id,
        "room_category": rt.room_category,
        "sharing_type": rt.sharing_type,
        "base_price": "5000",
    }

    serializer = RoomTypeSerializer(rt, data=data, partial=True)
    if serializer.is_valid():
        print("Update Validation SUCCESS")
    else:
        print(f"Update Validation FAILED: {serializer.errors}")

# Try to validate duplicate create
if rt:
    print("Testing duplicate create")
    data = {
        "hostel": rt.hostel.id,
        "room_category": rt.room_category,
        "sharing_type": rt.sharing_type,
        "base_price": "6000",
    }
    serializer = RoomTypeSerializer(data=data)
    if serializer.is_valid():
        print("Create Validation SUCCESS (SHOULD HAVE FAILED)")
    else:
        print(f"Create Validation FAILED Correctly: {serializer.errors}")
