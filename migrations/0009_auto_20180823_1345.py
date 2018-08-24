# Generated by Django 2.1 on 2018-08-23 16:45

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('monitor', '0008_auto_20180823_1153'),
    ]

    operations = [
        migrations.AlterField(
            model_name='host',
            name='circuit',
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='host',
            name='network',
            field=models.GenericIPAddressField(blank=True, null=True, protocol='IPv4'),
        ),
        migrations.AlterField(
            model_name='host',
            name='secretary',
            field=models.CharField(blank=True, max_length=200, null=True),
        ),
    ]
