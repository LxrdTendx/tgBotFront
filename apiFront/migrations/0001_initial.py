# Generated by Django 4.2.13 on 2024-06-21 09:31

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='User',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('chat_id', models.CharField(max_length=100, unique=True)),
                ('full_name', models.CharField(max_length=255)),
                ('is_authorized', models.BooleanField(default=False)),
            ],
        ),
    ]
