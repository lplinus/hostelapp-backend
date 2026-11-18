import uuid
import Hbackend.bunny_storage
import guestprofile.models
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('guestprofile', '0003_alter_guestprofile_aadhaar_card_file'),
    ]

    operations = [
        migrations.AddField(
            model_name='guestprofile',
            name='max_document_uploads',
            field=models.PositiveIntegerField(
                default=6,
                help_text='Maximum documents a guest can upload across self and members'
            ),
        ),
        migrations.AddField(
            model_name='guestprofile',
            name='aadhaar_original_name',
            field=models.CharField(
                blank=True,
                help_text='Original uploaded filename with extension',
                max_length=255,
                null=True
            ),
        ),
        migrations.CreateModel(
            name='GuestDocument',
            fields=[
                ('is_deleted', models.IntegerField(choices=[(0, 'Active'), (1, 'Deleted')], default=0)),
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('is_primary_guest', models.BooleanField(default=False, help_text="True if this is the primary guest's personal document (My Document)")),
                ('member_name', models.CharField(help_text='Full legal name of the primary guest or friend/member', max_length=255)),
                ('document_type', models.CharField(choices=[('aadhaar', 'Aadhaar Card'), ('passport', 'Passport'), ('driving_license', 'Driving License'), ('voter_id', 'Voter ID'), ('national_id', 'National ID'), ('other', 'Other Government ID')], default='aadhaar', help_text='Category of the document (separate from filename)', max_length=50)),
                ('document_number', models.CharField(blank=True, help_text='Optional identification number (e.g. Passport or Aadhaar number)', max_length=100, null=True)),
                ('file', models.FileField(help_text='Document file uploaded to Bunny CDN', storage=Hbackend.bunny_storage.BunnyCDNStorage(), upload_to=guestprofile.models.guest_document_upload_path, validators=[guestprofile.models.validate_id_document])),
                ('file_name', models.CharField(help_text='Original uploaded filename including extension', max_length=255)),
                ('file_size', models.PositiveIntegerField(default=0, help_text='File size in bytes')),
                ('booking_reference', models.CharField(blank=True, help_text='Associated booking reference code if uploaded for a booking', max_length=100, null=True)),
                ('verification_status', models.CharField(choices=[('unverified', 'Not Uploaded'), ('pending', 'Under Review'), ('verified', 'Verified'), ('rejected', 'Rejected')], default='verified', max_length=20)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('guest_profile', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='documents', to='guestprofile.guestprofile')),
            ],
            options={
                'verbose_name': 'Guest Document',
                'verbose_name_plural': 'Guest Documents',
                'ordering': ['-is_primary_guest', 'created_at'],
            },
        ),
    ]
