import apps.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0003_sitesettings_tiktok_url'),
    ]

    operations = [
        migrations.AddField(
            model_name='homesection',
            name='button2_label',
            field=models.CharField(blank=True, default='Explore events', help_text='Used by the Hero (top banner) only. Leave empty to hide the second button.', max_length=60, verbose_name='Second button label (Hero only)'),
        ),
        migrations.AddField(
            model_name='homesection',
            name='button2_url',
            field=models.CharField(blank=True, default='/events/', help_text='Page path like /events/ or a full web address.', max_length=300, verbose_name='Second button link (Hero only)'),
        ),
        migrations.AddField(
            model_name='sitesettings',
            name='footer_logo',
            field=models.ImageField(blank=True, help_text='Optional. Leave empty to use the built-in footer logo. Use a PNG with a transparent background that looks good on dark navy.', upload_to='branding/', validators=[apps.core.validators.validate_image_file], verbose_name='Footer logo override'),
        ),
        migrations.AddField(
            model_name='sitesettings',
            name='hero_emblem',
            field=models.ImageField(blank=True, help_text='Optional. The large picture beside the headline in the homepage top banner (shown on larger screens). Leave empty to use the built-in emblem. Use a PNG with a transparent background.', upload_to='branding/', validators=[apps.core.validators.validate_image_file], verbose_name='Homepage banner emblem'),
        ),
        migrations.AddField(
            model_name='sitesettings',
            name='intro_line_1',
            field=models.CharField(blank=True, default='import integrity, leadership', help_text='First line typed in the opening intro. Leave both lines empty to show only the logo.', max_length=60, verbose_name='Intro typing line 1'),
        ),
        migrations.AddField(
            model_name='sitesettings',
            name='intro_line_2',
            field=models.CharField(blank=True, default='character.build()  // ready', help_text='Second line typed in the opening intro. Anything after // is shown in green.', max_length=60, verbose_name='Intro typing line 2'),
        ),
        migrations.AddField(
            model_name='sitesettings',
            name='intro_logo',
            field=models.ImageField(blank=True, help_text='Optional. The logo shown at the end of the opening intro. Leave empty to use the built-in logo. Use a PNG with a transparent background that looks good on dark navy.', upload_to='branding/', validators=[apps.core.validators.validate_image_file], verbose_name='Intro logo override'),
        ),
    ]
