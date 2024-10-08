# Generated by Django 4.2.13 on 2024-07-01 06:20

from django.db import migrations
import jsonfield.fields


class Migration(migrations.Migration):

    dependencies = [
        ('apiFront', '0015_fronttransfer_photo_ids'),
    ]

    operations = [
        migrations.AlterField(
            model_name='fronttransfer',
            name='photo_ids',
            field=jsonfield.fields.JSONField(blank=True, default=list, null=True, verbose_name='ID фотографий'),
        ),
    ]
