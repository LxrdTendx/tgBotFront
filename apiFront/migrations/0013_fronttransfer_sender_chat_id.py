# Generated by Django 4.2.13 on 2024-06-26 08:52

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('apiFront', '0012_alter_fronttransfer_status'),
    ]

    operations = [
        migrations.AddField(
            model_name='fronttransfer',
            name='sender_chat_id',
            field=models.CharField(default=1, max_length=100, verbose_name='Chat ID отправителя'),
            preserve_default=False,
        ),
    ]
