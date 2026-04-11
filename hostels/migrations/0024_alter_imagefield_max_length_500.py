from django.db import migrations, models
import Hbackend.utils


class Migration(migrations.Migration):
    """
    Increases max_length of all ImageField columns from 100 → 500.

    Root cause: Django ImageField defaults to max_length=100 in the DB VARCHAR column.
    When storing full CDN URLs (ImageKit / Cloudinary) those can exceed 100 characters,
    causing MySQL's "Data too long for column" error.

    Affected models:
      - Hostel.og_image
      - HostelTypeImage.image
      - HostelImage.image, image2 … image10
      - DefaultHostelImage.image1 … image10
    """

    dependencies = [
        ('hostels', '0023_hostelimage_provider'),
    ]

    operations = [
        # ── Hostel.og_image ───────────────────────────────────────────
        migrations.AlterField(
            model_name='hostel',
            name='og_image',
            field=models.ImageField(
                blank=True,
                max_length=500,
                null=True,
                upload_to='seo/hostels/',
                validators=[Hbackend.utils.validate_image_size],
            ),
        ),

        # ── HostelTypeImage.image ─────────────────────────────────────
        migrations.AlterField(
            model_name='hosteltypeimage',
            name='image',
            field=models.ImageField(
                max_length=500,
                upload_to='hostel-type-images/',
                validators=[Hbackend.utils.validate_image_size],
            ),
        ),

        # ── HostelImage : image … image10 ─────────────────────────────
        migrations.AlterField(
            model_name='hostelimage',
            name='image',
            field=models.ImageField(
                max_length=500,
                upload_to='hostels/',
                validators=[Hbackend.utils.validate_image_size],
            ),
        ),
        migrations.AlterField(
            model_name='hostelimage',
            name='image2',
            field=models.ImageField(
                blank=True,
                max_length=500,
                null=True,
                upload_to='hostels/',
                validators=[Hbackend.utils.validate_image_size],
            ),
        ),
        migrations.AlterField(
            model_name='hostelimage',
            name='image3',
            field=models.ImageField(
                blank=True,
                max_length=500,
                null=True,
                upload_to='hostels/',
                validators=[Hbackend.utils.validate_image_size],
            ),
        ),
        migrations.AlterField(
            model_name='hostelimage',
            name='image4',
            field=models.ImageField(
                blank=True,
                max_length=500,
                null=True,
                upload_to='hostels/',
                validators=[Hbackend.utils.validate_image_size],
            ),
        ),
        migrations.AlterField(
            model_name='hostelimage',
            name='image5',
            field=models.ImageField(
                blank=True,
                max_length=500,
                null=True,
                upload_to='hostels/',
                validators=[Hbackend.utils.validate_image_size],
            ),
        ),
        migrations.AlterField(
            model_name='hostelimage',
            name='image6',
            field=models.ImageField(
                blank=True,
                max_length=500,
                null=True,
                upload_to='hostels/',
                validators=[Hbackend.utils.validate_image_size],
            ),
        ),
        migrations.AlterField(
            model_name='hostelimage',
            name='image7',
            field=models.ImageField(
                blank=True,
                max_length=500,
                null=True,
                upload_to='hostels/',
                validators=[Hbackend.utils.validate_image_size],
            ),
        ),
        migrations.AlterField(
            model_name='hostelimage',
            name='image8',
            field=models.ImageField(
                blank=True,
                max_length=500,
                null=True,
                upload_to='hostels/',
                validators=[Hbackend.utils.validate_image_size],
            ),
        ),
        migrations.AlterField(
            model_name='hostelimage',
            name='image9',
            field=models.ImageField(
                blank=True,
                max_length=500,
                null=True,
                upload_to='hostels/',
                validators=[Hbackend.utils.validate_image_size],
            ),
        ),
        migrations.AlterField(
            model_name='hostelimage',
            name='image10',
            field=models.ImageField(
                blank=True,
                max_length=500,
                null=True,
                upload_to='hostels/',
                validators=[Hbackend.utils.validate_image_size],
            ),
        ),

        # ── DefaultHostelImage : image1 … image10 ────────────────────
        migrations.AlterField(
            model_name='defaulthostelimage',
            name='image1',
            field=models.ImageField(
                blank=True,
                max_length=500,
                null=True,
                upload_to='hostels/defaults/',
                verbose_name='Default Image 1',
                validators=[Hbackend.utils.validate_image_size],
            ),
        ),
        migrations.AlterField(
            model_name='defaulthostelimage',
            name='image2',
            field=models.ImageField(
                blank=True,
                max_length=500,
                null=True,
                upload_to='hostels/defaults/',
                verbose_name='Default Image 2',
                validators=[Hbackend.utils.validate_image_size],
            ),
        ),
        migrations.AlterField(
            model_name='defaulthostelimage',
            name='image3',
            field=models.ImageField(
                blank=True,
                max_length=500,
                null=True,
                upload_to='hostels/defaults/',
                verbose_name='Default Image 3',
                validators=[Hbackend.utils.validate_image_size],
            ),
        ),
        migrations.AlterField(
            model_name='defaulthostelimage',
            name='image4',
            field=models.ImageField(
                blank=True,
                max_length=500,
                null=True,
                upload_to='hostels/defaults/',
                verbose_name='Default Image 4',
                validators=[Hbackend.utils.validate_image_size],
            ),
        ),
        migrations.AlterField(
            model_name='defaulthostelimage',
            name='image5',
            field=models.ImageField(
                blank=True,
                max_length=500,
                null=True,
                upload_to='hostels/defaults/',
                verbose_name='Default Image 5',
                validators=[Hbackend.utils.validate_image_size],
            ),
        ),
        migrations.AlterField(
            model_name='defaulthostelimage',
            name='image6',
            field=models.ImageField(
                blank=True,
                max_length=500,
                null=True,
                upload_to='hostels/defaults/',
                verbose_name='Default Image 6',
                validators=[Hbackend.utils.validate_image_size],
            ),
        ),
        migrations.AlterField(
            model_name='defaulthostelimage',
            name='image7',
            field=models.ImageField(
                blank=True,
                max_length=500,
                null=True,
                upload_to='hostels/defaults/',
                verbose_name='Default Image 7',
                validators=[Hbackend.utils.validate_image_size],
            ),
        ),
        migrations.AlterField(
            model_name='defaulthostelimage',
            name='image8',
            field=models.ImageField(
                blank=True,
                max_length=500,
                null=True,
                upload_to='hostels/defaults/',
                verbose_name='Default Image 8',
                validators=[Hbackend.utils.validate_image_size],
            ),
        ),
        migrations.AlterField(
            model_name='defaulthostelimage',
            name='image9',
            field=models.ImageField(
                blank=True,
                max_length=500,
                null=True,
                upload_to='hostels/defaults/',
                verbose_name='Default Image 9',
                validators=[Hbackend.utils.validate_image_size],
            ),
        ),
        migrations.AlterField(
            model_name='defaulthostelimage',
            name='image10',
            field=models.ImageField(
                blank=True,
                max_length=500,
                null=True,
                upload_to='hostels/defaults/',
                verbose_name='Default Image 10',
                validators=[Hbackend.utils.validate_image_size],
            ),
        ),
    ]
