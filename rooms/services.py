"""
Services for the Rooms application.
This module contains business logic for rooms, such as grouping rooms by hostel and category.
"""
from django.db.models import Prefetch
from .models import RoomType


class GroupedRoomsService:
    """
    Service class to handle complex room data transformations.
    Mainly used to group room types by their parent hostel and category for easier display on the frontend.
    """
    @staticmethod
    def get_grouped_rooms(user=None):
        """
        Retrieves and groups room types.
        If a user is provided, it filters rooms by hostels owned by that user.
        Returns a structured list of hostels, each containing their room categories and respective room data.
        """
        # Base queryset with optimization
        queryset = RoomType.objects.select_related("hostel").prefetch_related("beds")

        # Filter by owner if user is provided (for dashboard)
        if user:
            queryset = queryset.filter(hostel__owner=user)

        queryset = queryset.order_by("hostel__name", "room_category", "sharing_type")

        grouped_data = {}

        for room in queryset:
            hostel_id = room.hostel.id
            hostel_name = room.hostel.name

            if hostel_id not in grouped_data:
                grouped_data[hostel_id] = {"hostel_name": hostel_name, "categories": {}}

            cat_display = room.get_room_category_display()
            if cat_display not in grouped_data[hostel_id]["categories"]:
                grouped_data[hostel_id]["categories"][cat_display] = []

            grouped_data[hostel_id]["categories"][cat_display].append(
                {
                    "id": room.id,
                    "room_category": room.room_category,
                    "sharing": room.get_sharing_type_display(),
                    "sharing_type": room.sharing_type,
                    "price": room.base_price,
                    "price_per_day": room.price_per_day,
                    "total_beds": room.beds.count(),
                    "available_beds": room.beds.filter(is_available=True).count(),
                    "is_available": room.is_available,
                }
            )

        # Reformat into a list structure for the frontend
        result = []
        for hostel_id, hostel_info in grouped_data.items():
            categories_list = []
            for cat_name, rooms in hostel_info["categories"].items():
                categories_list.append({"category_name": cat_name, "rooms": rooms})

            result.append(
                {
                    "hostel_id": hostel_id,
                    "hostel_name": hostel_info["hostel_name"],
                    "categories": categories_list,
                }
            )

        return result
