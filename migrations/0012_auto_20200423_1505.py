# Generated by Django 3.0.3 on 2020-04-23 18:05

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('monitor', '0011_fibra_port'),
    ]

    operations = [
        migrations.AlterField(
            model_name='fibra',
            name='port',
            field=models.CharField(blank=True, max_length=20, null=True),
        ),
    ]
