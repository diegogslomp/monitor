# Generated by Django 3.2.13 on 2022-05-16 14:04

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('monitor', '0016_auto_20220509_0834'),
    ]

    operations = [
        migrations.RenameField(
            model_name='host',
            old_name='secretary',
            new_name='local',
        ),
    ]
