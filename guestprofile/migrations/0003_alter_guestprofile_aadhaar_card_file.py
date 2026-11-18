import Hbackend.bunny_storage
import guestprofile.models
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('guestprofile', '0002_guestprofile_share_id_with_host'),
    ]

    operations = [
        migrations.AlterField(
            model_name='guestprofile',
            name='aadhaar_card_file',
            field=models.FileField(
                blank=True,
                help_text='Aadhaar Card copy in PDF or Image format (PNG, JPG, WebP) stored on Bunny CDN',
                null=True,
                storage=Hbackend.bunny_storage.BunnyCDNStorage(),
                upload_to=guestprofile.models.guest_aadhaar_upload_path,
                validators=[guestprofile.models.validate_id_document],
            ),
        ),
    ]
