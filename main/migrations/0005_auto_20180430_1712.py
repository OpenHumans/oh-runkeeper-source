# Generated by Django 2.0.4 on 2018-04-30 17:12

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0004_auto_20180426_1741'),
    ]

    operations = [
        migrations.RenameField(
            model_name='datasourcemember',
            old_name='moves_id',
            new_name='runkeeper_id',
        ),
        migrations.AlterField(
            model_name='datasourcemember',
            name='last_submitted',
            field=models.DateTimeField(default='2018-04-23 17:11:59+00:00'),
        ),
        migrations.AlterField(
            model_name='datasourcemember',
            name='last_updated',
            field=models.DateTimeField(default='2018-04-23 17:11:59+00:00'),
        ),
        migrations.AlterField(
            model_name='datasourcemember',
            name='token_expires',
            field=models.DateTimeField(default='2018-04-30 17:11:59+00:00'),
        ),
    ]
