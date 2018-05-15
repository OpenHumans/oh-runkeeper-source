from django.core.management.base import BaseCommand
from main.models import DataSourceMember
from datauploader.tasks import process_runkeeper
import arrow
from datetime import timedelta


class Command(BaseCommand):
    help = 'Updates data for all members'

    def handle(self, *args, **options):
        users = DataSourceMember.objects.all()
        for runkeeper_user in users:
            if runkeeper_user.last_updated < (arrow.now() - timedelta(days=4)):
                oh_id = runkeeper_user.user.oh_id
                process_runkeeper.delay(oh_id)
            else:
                print("didn't update {}".format(runkeeper_user.runkeeper_id))
