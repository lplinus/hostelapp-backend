


from rest_framework import serializers
from .models import RoomType, Bed


class BedSerializer(serializers.ModelSerializer):
    class Meta:
        model = Bed
        fields = [
            "id",
            "bed_number",
            "is_available",
            "total_beds",
            "beds_available",
        ]


class RoomTypeSerializer(serializers.ModelSerializer):
    beds = BedSerializer(many=True, read_only=True)

    sharing_display = serializers.CharField(
        source="get_sharing_type_display",
        read_only=True,
    )

    category_display = serializers.CharField(
        source="get_room_category_display",
        read_only=True,
    )

    available_beds = serializers.SerializerMethodField()
    total_beds = serializers.SerializerMethodField()

    price = serializers.DecimalField(
        source="base_price", max_digits=10, decimal_places=2, required=False
    )

    class Meta:
        model = RoomType
        fields = [
            "id",
            "hostel",
            "room_category",
            "category_display",
            "sharing_type",
            "sharing_display",
            "base_price",
            "price",
            "price_per_day",
            "is_available",
            "total_beds",
            "available_beds",
            "beds",
        ]

    def get_total_beds(self, obj):
        # Prefer the total_beds field if any bed object has it filled (e.g. bulk inventory mode)
        # Otherwise count the individual bed objects
        beds = obj.beds.all()
        if not beds.exists():
            return 0

        # If the first bed has a numeric count, we assume it's in bulk mode
        # We sum them up in case there are multiple bulk entries
        total = sum((b.total_beds or 0) for b in beds)
        if total > 0:
            return total
        return beds.count()

    def get_available_beds(self, obj):
        # Prefer the beds_available field if any bed object has it filled
        # Otherwise count individual available items
        beds = obj.beds.all()
        if not beds.exists():
            return 0

        available = sum((b.beds_available or 0) for b in beds if b.is_available)
        if available > 0:
            return available

        # Fallback to counting individual available bed objects
        return beds.filter(is_available=True).count()

    def create(self, validated_data):
        total_beds_to_create = self.initial_data.get("total_beds")
        room_type = super().create(validated_data)

        if total_beds_to_create:
            try:
                count = int(total_beds_to_create)
                for i in range(count):
                    Bed.objects.create(
                        room_type=room_type, bed_number=f"B-{i + 1}", is_available=True
                    )
            except ValueError:
                pass

        return room_type

    def update(self, instance, validated_data):
        total_beds_requested = self.initial_data.get("total_beds")
        instance = super().update(instance, validated_data)

        if total_beds_requested is not None:
            try:
                new_total = int(total_beds_requested)
                current_total = instance.beds.count()

                if new_total > current_total:
                    # Add beds
                    for i in range(current_total, new_total):
                        Bed.objects.create(
                            room_type=instance,
                            bed_number=f"B-{i + 1}",
                            is_available=True,
                        )
                elif new_total < current_total:
                    # Remove beds - only remove available beds starting from the last ones
                    diff = current_total - new_total
                    beds_to_remove = instance.beds.filter(is_available=True).order_by(
                        "-id"
                    )[:diff]
                    for bed in beds_to_remove:
                        bed.delete()
            except ValueError:
                pass

        return instance
