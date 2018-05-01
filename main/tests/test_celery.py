from datauploader.tasks import process_runkeeper
from django.test import TestCase
from freezegun import freeze_time
from django.conf import settings
import vcr
from open_humans.models import OpenHumansMember
from main.models import DataSourceMember
import arrow


class CeleryTestCase(TestCase):
    """
    test that celery processing works
    """

    def setUp(self):
        settings.OPENHUMANS_CLIENT_ID = 'oh_client_id'
        settings.OPENHUMANS_CLIENT_SECRET = 'oh_client_secret'
        settings.RUNKEEPER_CLIENT_ID = 'RUNKEEPER_CLIENT_ID'
        settings.RUNKEEPER_CLIENT_SECRET = 'RUNKEEPER_CLIENT_SECRET'
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
        oh_member = OpenHumansMember.objects.get(oh_id=23456789)
        process_runkeeper(oh_member.oh_id)
        runkeeper_member = DataSourceMember.objects.get(runkeeper_id=12345678)
        self.assertEqual(runkeeper_member.last_updated, arrow.get('2016-06-24'))
