
from django.db import migrations, models
import json

def convert_to_json(apps, schema_editor):
    Hostel = apps.get_model('hostels', 'Hostel')
    for hostel in Hostel.objects.all():
        val = getattr(hostel, 'suitable_for', 'anyone')
        if not val or val == 'anyone':
            hostel.suitable_for = '[]'
        else:
            # Wrap existing string choice in a JSON list
            hostel.suitable_for = json.dumps([val])
        hostel.save()

class Migration(migrations.Migration):

    dependencies = [
        ('hostels', '0027_hostel_suitable_for'),
    ]

    operations = [
        migrations.RunPython(convert_to_json),
        migrations.AlterField(
            model_name='hostel',
            name='suitable_for',
            field=models.JSONField(blank=True, default=list, help_text='Selected suitable categories (student, job_holder, etc.)'),
        ),
    ]
