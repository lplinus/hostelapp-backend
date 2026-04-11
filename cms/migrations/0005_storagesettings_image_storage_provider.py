from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cms', '0004_storagesettings'),
    ]

    operations = [
        migrations.AddField(
            model_name='storagesettings',
            name='image_storage_provider',
            field=models.CharField(
                choices=[
                    ('imagekit', 'ImageKit (Primary) + Cloudinary (Fallback)'),
                    ('cloudinary', 'Cloudinary (Primary) + ImageKit (Fallback)'),
                ],
                default='imagekit',
                help_text=(
                    'Select the primary image storage service for hostel images. '
                    'The other service acts as automatic fallback if the primary fails.'
                ),
                max_length=20,
            ),
        ),
    ]
