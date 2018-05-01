from django.core.management.base import BaseCommand
from open_humans.models import OpenHumansMember
from main.models import DataSourceMember
from django.conf import settings
from datauploader.tasks import process_runkeeper
import requests
#import vcr


class Command(BaseCommand):
    help = 'Import existing users from legacy project'

    def add_arguments(self, parser):
        parser.add_argument('--infile', type=str,
                            help='CSV with project_member_id & refresh_token')
        parser.add_argument('--delimiter', type=str,
                            help='CSV delimiter')

    # @vcr.use_cassette('import_users.yaml', decode_compressed_response=True)
    def handle(self, *args, **options):
        for line in open(options['infile']):
            line = line.strip().split(options['delimiter'])
            oh_id = line[0]
            oh_refresh_token = line[1]
            runkeeper_access_token = line[2]
            if len(OpenHumansMember.objects.filter(
                     oh_id=oh_id)) == 0:
                oh_member = OpenHumansMember.create(
                                    oh_id=oh_id,
                                    access_token="mock",
                                    refresh_token=oh_refresh_token,
                                    expires_in=-3600)
                oh_member.save()
                oh_member._refresh_tokens(
                    client_id=settings.OPENHUMANS_CLIENT_ID,
                    client_secret=settings.OPENHUMANS_CLIENT_SECRET)
                oh_member = OpenHumansMember.objects.get(oh_id=oh_id)

                headers = {'Authorization': 'Bearer {}'.format(
                            runkeeper_access_token)}
                profile_url = 'https://api.runkeeper.com/user'
                profile_response = requests.get(profile_url, headers=headers)
                user_data = profile_response.json()
                runkeeper_id = user_data['userID']

                runkeeper_member = DataSourceMember(
                    access_token=runkeeper_access_token,
                    runkeeper_id=runkeeper_id)
                runkeeper_member.user = oh_member
                runkeeper_member.save()
                process_runkeeper.delay(oh_member.oh_id)
