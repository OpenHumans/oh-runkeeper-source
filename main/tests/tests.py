from django.test import TestCase
from freezegun import freeze_time
from django.conf import settings
from django.core.management import call_command
import vcr
from open_humans.models import OpenHumansMember
from main.models import DataSourceMember
import arrow
from datauploader.celery import app
from main.management.commands import import_users


class ManagementTestCase(TestCase):
    """
    test that files are parsed correctly
    """

    def setUp(self):
        settings.OPENHUMANS_CLIENT_ID = 'oh_client_id'
        settings.OPENHUMANS_CLIENT_SECRET = 'oh_client_secret'
        settings.RUNKEEPER_CLIENT_ID = 'RUNKEEPER_CLIENT_ID'
        settings.RUNKEEPER_CLIENT_SECRET = 'RUNKEEPER_CLIENT_SECRET'
        app.conf.update(task_always_eager=True)

    @freeze_time('2016-06-24')
    @vcr.use_cassette('main/tests/fixtures/import_users.yaml',
                      record_mode='none')
    def test_import_command(self):
        self.assertEqual(len(OpenHumansMember.objects.all()),
                         0)
        self.assertEqual(len(DataSourceMember.objects.all()),
                         0)
        cmd = import_users.Command()
        cmd.handle(infile='main/tests/fixtures/import_list.txt',
                       delimiter=",")
        self.assertEqual(len(OpenHumansMember.objects.all()),
                         1)
        self.assertEqual(len(DataSourceMember.objects.all()),
                         1)
        self.assertEqual(len(DataSourceMember.objects.filter(runkeeper_id=12345678)),
                         1)


class UpdateTestCase(TestCase):
    """
    test that periodic updates pass
    """

    def setUp(self):
        settings.OPENHUMANS_CLIENT_ID = 'oh_client_id'
        settings.OPENHUMANS_CLIENT_SECRET = 'oh_client_secret'
        settings.RUNKEEPER_CLIENT_ID = 'RUNKEEPER_CLIENT_ID'
        settings.RUNKEEPER_CLIENT_SECRET = 'RUNKEEPER_CLIENT_SECRET'
        app.conf.update(task_always_eager=True)
        oh_member = OpenHumansMember.create(
                            oh_id=23456789,
                            access_token="new_oh_access_token",
                            refresh_token="new_oh_refresh_token",
                            expires_in=36000)
        oh_member.save()
        runkeeper_member = DataSourceMember(
            runkeeper_id=12345678,
            access_token="new_moves_access_token",
            last_updated=arrow.get('2016-06-19').format(),
            last_submitted=arrow.get('2016-06-19').format()
        )
        runkeeper_member.user = oh_member
        runkeeper_member.save()

    @freeze_time('2016-06-24')
    @vcr.use_cassette('main/tests/fixtures/import_users.yaml',
                      record_mode='none')
    def test_update_command(self):
        call_command('update_data')
        runkeeper_member = DataSourceMember.objects.get(runkeeper_id=12345678)
        self.assertEqual(runkeeper_member.last_updated, arrow.get('2016-06-24'))
