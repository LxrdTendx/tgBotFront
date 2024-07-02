# Generated by Django 4.2.13 on 2024-06-25 12:18

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('apiFront', '0009_fronttransfer_created_at_alter_fronttransfer_sender'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='fronttransfer',
            name='photos',
        ),
        migrations.AddField(
            model_name='fronttransfer',
            name='photo1',
            field=models.ImageField(blank=True, null=True, upload_to='photos/', verbose_name='Фото 1'),
        ),
        migrations.AddField(
            model_name='fronttransfer',
            name='photo2',
            field=models.ImageField(blank=True, null=True, upload_to='photos/', verbose_name='Фото 2'),
        ),
        migrations.AddField(
            model_name='fronttransfer',
            name='photo3',
            field=models.ImageField(blank=True, null=True, upload_to='photos/', verbose_name='Фото 3'),
        ),
        migrations.AddField(
            model_name='fronttransfer',
            name='photo4',
            field=models.ImageField(blank=True, null=True, upload_to='photos/', verbose_name='Фото 4'),
        ),
        migrations.AddField(
            model_name='fronttransfer',
            name='photo5',
            field=models.ImageField(blank=True, null=True, upload_to='photos/', verbose_name='Фото 5'),
        ),
    ]
