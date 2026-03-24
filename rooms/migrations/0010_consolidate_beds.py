# Data migration to consolidate individual Bed rows into a single row per RoomType.
# This merges all existing bed rows (B-1, B-2, ..., B-N) into one row with:
#   - total_beds = count of all beds
#   - beds_available = count of available beds
#   - bed_number = "B-1,B-2,...,B-N" (comma-separated)

from django.db import migrations


def consolidate_beds(apps, schema_editor):
    """
    For each RoomType, merge all individual Bed rows into a single consolidated row.
    Preserves the occupied/available state accurately.
    """
    RoomType = apps.get_model("rooms", "RoomType")
    Bed = apps.get_model("rooms", "Bed")

    for room_type in RoomType.objects.all():
        beds = list(room_type.beds.all().order_by("id"))

        if len(beds) <= 1:
            # Already consolidated or no beds — update fields if needed
            if len(beds) == 1:
                bed = beds[0]
                # If total_beds is not set, this is a legacy individual row
                if not bed.total_beds or bed.total_beds == 0:
                    bed.total_beds = 1
                    bed.beds_available = 1 if bed.is_available else 0
                    bed.save()
            continue

        # Multiple bed rows exist — consolidate them
        total_count = len(beds)
        available_count = sum(1 for b in beds if b.is_available)

        # Collect all bed numbers
        bed_numbers = []
        for b in beds:
            if b.bed_number:
                bed_numbers.append(b.bed_number)

        consolidated_bed_number = ",".join(bed_numbers)

        # Keep the first bed row and update it with consolidated data
        first_bed = beds[0]
        first_bed.bed_number = consolidated_bed_number
        first_bed.total_beds = total_count
        first_bed.beds_available = available_count
        first_bed.is_available = available_count > 0
        first_bed.save()

        # Delete all other bed rows for this room type
        ids_to_delete = [b.id for b in beds[1:]]
        Bed.objects.filter(id__in=ids_to_delete).delete()


def reverse_consolidation(apps, schema_editor):
    """
    Reverse migration: Split consolidated Bed rows back into individual rows.
    """
    RoomType = apps.get_model("rooms", "RoomType")
    Bed = apps.get_model("rooms", "Bed")

    for room_type in RoomType.objects.all():
        bed = room_type.beds.first()
        if not bed or not bed.bed_number:
            continue

        # Split comma-separated bed numbers
        bed_numbers = [b.strip() for b in bed.bed_number.split(",") if b.strip()]

        if len(bed_numbers) <= 1:
            continue

        # Determine how many are available vs occupied
        total = bed.total_beds or len(bed_numbers)
        available = bed.beds_available or total
        occupied = total - available

        # Create individual bed rows
        for i, bed_num in enumerate(bed_numbers):
            if i == 0:
                # Update the first bed to be a single bed
                bed.bed_number = bed_num
                bed.total_beds = None
                bed.beds_available = None
                bed.is_available = i >= occupied  # First N beds are occupied
                bed.save()
            else:
                Bed.objects.create(
                    room_type=room_type,
                    bed_number=bed_num,
                    total_beds=None,
                    beds_available=None,
                    is_available=i >= occupied,
                )


class Migration(migrations.Migration):

    dependencies = [
        ("rooms", "0009_alter_bed_bed_number"),
    ]

    operations = [
        migrations.RunPython(consolidate_beds, reverse_consolidation),
    ]
