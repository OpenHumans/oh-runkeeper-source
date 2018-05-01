from ohapi import api
from django.conf import settings
import arrow
from datetime import timedelta


def get_runkeeper_file(oh_member):
    try:
        oh_access_token = oh_member.get_access_token(
                            client_id=settings.OPENHUMANS_CLIENT_ID,
                            client_secret=settings.OPENHUMANS_CLIENT_SECRET)
        user_object = api.exchange_oauth2_member(oh_access_token)
        files = {}
        for dfile in user_object['data']:
            if 'Runkeeper' in dfile['metadata']['tags']:
                files[dfile['basename']] = dfile['download_url']
        return files
    except:
        return 'error'


def check_update(runkeeper_member):
    if runkeeper_member.last_submitted < (arrow.now() - timedelta(hours=1)):
        return True
    return False
