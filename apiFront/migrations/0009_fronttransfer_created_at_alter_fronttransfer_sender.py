# Generated by Django 4.2.13 on 2024-06-25 11:22

from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('apiFront', '0008_alter_fronttransfer_sender'),
    ]

    operations = [
        migrations.AddField(
            model_name='fronttransfer',
            name='created_at',
            field=models.DateTimeField(default=django.utils.timezone.now, verbose_name='Дата создания'),
        ),
        migrations.AlterField(
            model_name='fronttransfer',
            name='sender',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='sent_transfers', to='apiFront.user', verbose_name='Отправитель'),
        ),
    ]
