"""
Asynchronous tasks that update data in Open Humans.
These tasks:
  1. delete any current files in OH if they match the planned upload filename
  2. adds a data file
"""
import logging
import json
import tempfile
import requests
import os
from celery import shared_task
from django.conf import settings
from open_humans.models import OpenHumansMember
from datetime import datetime, timedelta
from ohapi import api
import arrow

# Set up logging.
logger = logging.getLogger(__name__)

BACKGROUND_DATA_KEYS = ['timestamp', 'steps', 'calories_burned', 'source']
FITNESS_SUMMARY_KEYS = ['type', 'equipment', 'start_time', 'utc_offset',
                        'total_distance', 'duration', 'total_calories',
                        'climb', 'source']
FITNESS_PATH_KEYS = ['latitude', 'longitude', 'altitude', 'timestamp', 'type']

PAGESIZE = '10000'


def data_for_keys(data_dict, data_keys):
    """
    Return a dict with data for requested keys, or empty strings if missing.
    """
    return {x: data_dict[x] if x in data_dict else '' for x in data_keys}


def yearly_items(items):
    current_year = (datetime.now() - timedelta(days=1)).year

    result = {}
    complete_years = []

    for item in items:
        try:
            time_string = item['start_time']
        except KeyError:
            time_string = item['timestamp']

        start_time = datetime.strptime(time_string, '%a, %d %b %Y %H:%M:%S')

        if start_time.year not in result:
            result[start_time.year] = []

            if start_time.year < current_year:
                complete_years.append(start_time.year)

        result[start_time.year].append(item)

    return result, complete_years


def runkeeper_query(path, access_token, content_type=None):
    """
    Query RunKeeper API and return data.
    """
    headers = {'Authorization': 'Bearer {}'.format(access_token)}

    if content_type:
        headers['Content-Type'] = content_type

    data_url = 'https://api.runkeeper.com{}'.format(path)

    data_response = requests.get(data_url, headers=headers)
    data = data_response.json()

    return data


def get_items(path, access_token, recurse='both'):
    """
    Iterate to get all items for a given access_token and path.

    RunKeeper uses the same pages format for items in various places.
    """
    query_data = runkeeper_query(path, access_token)
    items = query_data['items']

    if 'previous' in query_data and recurse in ['both', 'prev']:
        prev_items = get_items(query_data['previous'], access_token,
                               recurse='prev')
        items = prev_items + items

    if 'next' in query_data and recurse in ['both', 'next']:
        next_items = get_items(query_data['next'],
                               access_token,
                               recurse='next')
        items = items + next_items

    if recurse == 'both':
        # Assert we have correct size.
        if len(items) != query_data['size']:
            error_msg = ('Activity items for retrieved for {} ({}) '
                         "doesn't match expected array size ({})").format(
                             path, len(items), query_data['size'])
            raise AssertionError(error_msg)

    return items


@shared_task
def process_runkeeper(oh_id):
    """
    Data is split per-year, in JSON format.
    Each JSON is an object (dict) in the following format (pseudocode):

    { 'background_activities':
        [
          { key: value for each of BACKGROUND_DATA_KEYS },
          { key: value for each of BACKGROUND_DATA_KEYS },
          ...
        ],
      'fitness_activities':
        [
          { 'path': { key: value for each of FITNESS_PATH_KEYS },
             and key: value for each of the FITNESS_ACTIVITY_KEYS },
          { 'path': { key: value for each of FITNESS_PATH_KEYS },
             and key: value for each of the FITNESS_ACTIVITY_KEYS },
          ...
        ]
    }

    Notes:
        - items are sorted according to start_time or timestamp
        - The item_uri for fitness_activities matches item_uri in
          fitness_activity_sharing.
    """
    oh_member = OpenHumansMember.objects.get(oh_id=oh_id)
    oh_access_token = oh_member.get_access_token(
                            client_id=settings.OPENHUMANS_CLIENT_ID,
                            client_secret=settings.OPENHUMANS_CLIENT_SECRET)
    runkeeper_member = oh_member.datasourcemember
    print('start processing data for {}'.format(
                            runkeeper_member.runkeeper_id))

    access_token = runkeeper_member.access_token
    user_data = runkeeper_query('/user', access_token)
    runkeeper_member.runkeeper_id = user_data['userID']

    # Get activity data.
    fitness_activity_path = '{}?pageSize={}'.format(
        user_data['fitness_activities'], PAGESIZE)
    fitness_activity_items, complete_fitness_activity_years = yearly_items(
        get_items(path=fitness_activity_path, access_token=access_token))

    # Background activities.
    background_activ_path = '{}?pageSize={}'.format(
        user_data['background_activities'], PAGESIZE)
    background_activ_items, complete_background_activ_years = yearly_items(
        get_items(background_activ_path, access_token))

    all_years = sorted(set(list(fitness_activity_items.keys()) +
                           list(background_activ_items.keys())))
    all_completed_years = set(
        complete_fitness_activity_years + complete_background_activ_years)

    for year in all_years:
        outdata = {'fitness_activities': [],
                   'background_activities': []}

        fitness_items = sorted(
            fitness_activity_items.get(year, []),
            key=lambda item: datetime.strptime(
                item['start_time'], '%a, %d %b %Y %H:%M:%S'))
        for item in fitness_items:
            item_data = runkeeper_query(item['uri'], access_token)
            item_data_out = data_for_keys(item_data, FITNESS_SUMMARY_KEYS)
            item_data_out['path'] = [
                data_for_keys(datapoint, FITNESS_PATH_KEYS)
                for datapoint in item_data['path']]
            outdata['fitness_activities'].append(item_data_out)
        background_items = sorted(
            background_activ_items.get(year, []),
            key=lambda item: datetime.strptime(
                item['timestamp'], '%a, %d %b %Y %H:%M:%S'))

        for item in background_items:
            outdata['background_activities'].append(
                data_for_keys(item, BACKGROUND_DATA_KEYS))

        filename = 'Runkeeper-activity-data-{}.json'.format(str(year))
        temp_directory = tempfile.mkdtemp()
        filepath = os.path.join(temp_directory, filename)
        with open(filepath, 'w') as f:
            json.dump(outdata, f, indent=2, sort_keys=True)
            f.flush()

        metadata = {
            'description': ('Runkeeper GPS maps and imported '
                            'activity data.'),
            'tags': ['GPS', 'Runkeeper'],
            'dataYear': year,
            'complete': year in all_completed_years,
        }
        api.delete_file(oh_member.access_token,
                        oh_member.oh_id,
                        file_basename=filename)
        api.upload_aws(filepath, metadata,
                       oh_access_token,
                       project_member_id=oh_member.oh_id)
    runkeeper_member.last_updated = arrow.now().format()
    runkeeper_member.save()
    print('finished processing data for {}'.format(
                            runkeeper_member.runkeeper_id))
