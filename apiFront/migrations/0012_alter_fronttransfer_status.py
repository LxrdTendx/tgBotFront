# Generated by Django 4.2.13 on 2024-06-26 06:46

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('apiFront', '0011_alter_fronttransfer_floor'),
    ]

    operations = [
        migrations.AlterField(
            model_name='fronttransfer',
            name='status',
            field=models.CharField(choices=[('transferred', 'Передано'), ('approved', 'Одобрено'), ('with_remarks', 'Есть замечания'), ('on_consideration', 'На рассмотрении')], max_length=20, verbose_name='Статус'),
        ),
    ]
