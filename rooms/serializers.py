

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
    features_list = serializers.SerializerMethodField()

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
            "show_this_price",
            "features",
            "features_list",
            "total_beds",
            "available_beds",
            "beds",
        ]

    def get_features_list(self, obj):
        """
        Splits the comma-separated features string into a list.
        Returns an empty list if no features are set.
        """
        if obj.features and obj.features.strip():
            return [f.strip() for f in obj.features.split(",") if f.strip()]
        return []

    def get_total_beds(self, obj):
        """
        Reads total_beds from the single consolidated Bed row.
        Falls back to counting individual rows for backward compatibility.
        """
        bed = obj.beds.first()
        if not bed:
            return 0

        # Consolidated mode: read from the total_beds field
        if bed.total_beds and bed.total_beds > 0:
            return bed.total_beds

        # Fallback: count individual bed rows (legacy data)
        return obj.beds.count()

    def get_available_beds(self, obj):
        """
        Reads beds_available from the single consolidated Bed row.
        Falls back to counting individual available rows for backward compatibility.
        """
        bed = obj.beds.first()
        if not bed:
            return 0

        # Consolidated mode: read from the beds_available field
        if bed.beds_available is not None and bed.beds_available >= 0:
            return bed.beds_available

        # Fallback: count individual available bed rows (legacy data)
        return obj.beds.filter(is_available=True).count()

    def create(self, validated_data):
        total_beds_to_create = self.initial_data.get("total_beds")
        room_type = super().create(validated_data)

        if total_beds_to_create:
            try:
                count = int(total_beds_to_create)
                # --- Consolidated Mode: Single row with all bed numbers ---
                bed_numbers = ",".join([f"B-{i + 1}" for i in range(count)])
                Bed.objects.create(
                    room_type=room_type,
                    bed_number=bed_numbers,
                    total_beds=count,
                    beds_available=count,
                    is_available=True,
                )

                # --- Individual Bed Mode (for future bed assignment) ---
                # Uncomment the block below and comment out the block above
                # to create individual bed rows for per-bed tracking.
                #
                # for i in range(count):
                #     Bed.objects.create(
                #         room_type=room_type,
                #         bed_number=f"B-{i + 1}",
                #         is_available=True,
                #     )

            except ValueError:
                pass

        return room_type

    def update(self, instance, validated_data):
        total_beds_requested = self.initial_data.get("total_beds")
        instance = super().update(instance, validated_data)

        if total_beds_requested is not None:
            try:
                new_total = int(total_beds_requested)

                # --- Consolidated Mode: Update the single Bed row ---
                bed = instance.beds.first()

                if bed:
                    # Recalculate: keep the occupied count, adjust available
                    occupied = (bed.total_beds or 0) - (bed.beds_available or 0)
                    new_available = max(0, new_total - occupied)

                    # Regenerate bed numbers
                    bed_numbers = ",".join([f"B-{i + 1}" for i in range(new_total)])

                    bed.total_beds = new_total
                    bed.beds_available = new_available
                    bed.bed_number = bed_numbers
                    bed.is_available = new_available > 0
                    bed.save()

                    # Delete any extra legacy rows if they exist
                    extra_beds = instance.beds.exclude(pk=bed.pk)
                    if extra_beds.exists():
                        extra_beds.delete()
                else:
                    # No bed row exists yet, create one
                    bed_numbers = ",".join([f"B-{i + 1}" for i in range(new_total)])
                    Bed.objects.create(
                        room_type=instance,
                        bed_number=bed_numbers,
                        total_beds=new_total,
                        beds_available=new_total,
                        is_available=True,
                    )

                # --- Individual Bed Mode (for future bed assignment) ---
                # Uncomment the block below and comment out the block above
                # to manage individual bed rows for per-bed tracking.
                #
                # current_total = instance.beds.count()
                # if new_total > current_total:
                #     for i in range(current_total, new_total):
                #         Bed.objects.create(
                #             room_type=instance,
                #             bed_number=f"B-{i + 1}",
                #             is_available=True,
                #         )
                # elif new_total < current_total:
                #     diff = current_total - new_total
                #     beds_to_remove = instance.beds.filter(is_available=True).order_by(
                #         "-id"
                #     )[:diff]
                #     for bed_obj in beds_to_remove:
                #         bed_obj.delete()

            except ValueError:
                pass

        return instance
