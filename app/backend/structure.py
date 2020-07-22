# Copyright 2020 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""This module is a part of the UAC AssetMG tool.

there are two ways to use this module:
1. "get_struct" function creates a json with two 'structure' objects,
the first one is the top MCC account structure down to the asset level, and the
second one is a mapping from each asset to its adgroups.
2. "create_mcc_struct" function returns an account structure down to assets, and
creates an asset-to-adgroup mapping json, to be used later.
"""

import json
from googleads import adwords
from app.backend.service import Service_Class
from pathlib import Path

ASSET_TYPE_MAP = {
    'TextAsset': 'TEXT',
    'ImageAsset': 'IMAGE',
    'YoutubeVideoAsset': 'YOUTUBE_VIDEO',
    'MediaBundleAsset': 'MEDIA_BUNDLE'
}

PAGE_SIZE = 500
PATH = Path('./')
asset_to_ag_json_path = Path('app/cache/asset_to_ag.json')
account_struct_json_path = Path('app/cache/account_struct.json')

def create_mcc_struct(client):
  """create the full structure of an mcc account down to asset level."""
  accounts = get_accounts(client)
  _revert_json()

  for account in accounts:
    account['campaigns'] = get_campaigns(client, account['id'])

  with open(account_struct_json_path, 'w') as f:
    json.dump(accounts, f,indent=2)

  Service_Class.reset_cid(client)
  return accounts


def create_account_struct(client,account):
  _revert_json()
  return get_campaigns(client,account)


def get_accounts(client):
  """get all non-mcc accounts."""
  managed_customer_service = Service_Class.get_managed_customer_service(client)

  offset = 0
  selector = {
      'fields': ['CustomerId', 'Name'],
      'paging': {
          'startIndex': str(offset),
          'numberResults': str(PAGE_SIZE)
      }
  }
  more_pages = True
  accounts = []
  mcc_accounts = []
  acc = {}

  while more_pages:
    page = managed_customer_service.get(selector)
    if 'entries' in page and page['entries']:
      for account in page['entries']:
        acc['name'] = account['name']
        acc['id'] = account['customerId']
        accounts.append(acc)
        acc = {}

    if 'links' in page and page['links']:
      for account in page['links']:
        mcc_accounts.append(account['managerCustomerId'])

    offset += PAGE_SIZE
    selector['paging']['startIndex'] = str(offset)
    more_pages = offset < int(page['totalNumEntries'])

  # Remove MCC accounts from account list
  for mcc in set(mcc_accounts):
    for account in accounts:
      if mcc == account['id']:
        accounts.remove(account)

  return accounts


def get_campaigns(client, account):
  """Create campaign structure down to asset level."""
  campaign_service = Service_Class.get_campaign_service(client)
  client.SetClientCustomerId(account)
  campaigns = []
  camp = {}
  # Construct selector and get all campaigns.
  offset = 0
  selector = {
      'fields': ['Id', 'Name', 'Status', 'Settings'],
      'paging': {
          'startIndex': str(offset),
          'numberResults': str(PAGE_SIZE)
      }
  }

  more_pages = True
  while more_pages:
    page = campaign_service.get(selector)

    # Display results.
    if 'entries' in page:
      for campaign in page['entries']:
        if campaign['settings'][1][
            'Setting.Type'] == 'UniversalAppCampaignSetting':
          camp['campaign_name'] = campaign['name']
          camp['id'] = campaign['id']
          camp['adgroups'] = _get_adgroups(client, campaign['id'])
          campaigns.append(camp)
          camp = {}

    else:
      print('No campaigns were found.')
    offset += PAGE_SIZE
    selector['paging']['startIndex'] = str(offset)
    more_pages = offset < int(page['totalNumEntries'])

  return campaigns


def _get_adgroups(client, c_id):
  """Create adgroups structure down to asset level."""
  ad_group_service = Service_Class.get_ad_group_service(client)

  adgroups = []
  ag = {}
  # Construct selector and get all ad groups.
  offset = 0
  selector = {
      'fields': ['Id', 'Name', 'Status'],
      'predicates': [
          {
              'field': 'CampaignId',
              'operator': 'EQUALS',
              'values': c_id
          }
      ],
      'paging': {
          'startIndex': str(offset),
          'numberResults': str(PAGE_SIZE)
      }
  }

  more_pages = True
  while more_pages:
    page = ad_group_service.get(selector)

    if 'entries' in page:
      for ad_group in page['entries']:
        ag['name'] = ad_group['name']
        ag['id'] = ad_group['id']
        ag['assets'] = get_assets_from_adgroup(client, ad_group['id'])
        adgroups.append(ag)
        create_asset_struct(ag)
        ag = {}
    else:
      print('No ad groups were found.')
    offset += PAGE_SIZE
    selector['paging']['startIndex'] = str(offset)
    more_pages = offset < int(page['totalNumEntries'])

    return adgroups


def get_assets_from_adgroup(client, ag_id):
  """Get all assets of a given adgroup."""

  adgroupad_service = Service_Class.get_ad_group_ad_service(client)

  ag_assets = []

  offset = 0
  selector = {
      'fields': [
          'UniversalAppAdImages', 'UniversalAppAdHeadlines',
          'UniversalAppAdDescriptions', 'UniversalAppAdYouTubeVideos',
          'UniversalAppAdHtml5MediaBundles'
      ],
      'predicates': [{
          'field': 'AdGroupId',
          'operator': 'EQUALS',
          'values': [ag_id]
      }],
      'paging': {
          'startIndex': str(offset),
          'numberResults': str(PAGE_SIZE)
      }
  }

  more_pages = True
  while more_pages:
    page = adgroupad_service.get(selector)
    for i in page['entries']:
      ag_assets.extend(_extract_assets_data(i['ad']))

    offset += PAGE_SIZE
    selector['paging']['startIndex'] = str(offset)
    more_pages = offset < int(page['totalNumEntries'])

  return ag_assets


def _extract_assets_data(ad):
  """Constract the asset object with relative fields."""
  ag_assets = []
  asset = {}
  ASSET_TYPES = [
      'headlines', 'descriptions', 'images', 'videos', 'html5MediaBundles'
  ]
  ASSET_TYPS_TEXT = ['headlines', 'descriptions']
  yt_url_prefix = 'https://www.youtube.com/watch?v='
  yt_thumbnail_url = 'https://img.youtube.com/vi/%s/1.jpg'

  for entry in ad:
    if entry in ASSET_TYPES and len(ad[entry]):
      # Get all asset propererties by asset type
      for item in ad[entry]:
        asset['id'] = item['asset']['assetId']
        asset['name'] = item['asset']['assetName']
        asset['type'] = ASSET_TYPE_MAP[item['asset']['Asset.Type']]
        if entry in ASSET_TYPS_TEXT:
          asset['text_type'] = entry
          asset['asset_text'] = item['asset']['assetText']
        if entry == 'images':
          asset['image_url'] = item['asset']['fullSizeInfo']['imageUrl']
        if entry == 'videos':
          asset['video_id'] = item['asset']['youTubeVideoId']
          asset['link'] = yt_url_prefix + asset['video_id']
          asset['image_url'] = yt_thumbnail_url%(asset['video_id'])

        ag_assets.append(asset)
        asset = {}

  return ag_assets


def create_asset_struct(ag):
  """Build the asset-to-adgroup structure in a json file, one adgroup at a time."""

  ag_id = ag['id']
  assets = ag['assets']

  with open(asset_to_ag_json_path, 'r') as f:
    data = json.load(f)

  for asset in assets:
    add_entry = True
    for entry in data:
      if entry['id'] == asset['id'] and entry.get('text_type') == asset.get(
          'text_type'):
        add_entry = False
        if ag_id not in entry['adgroups']:
          entry['adgroups'].append(ag_id)

    if add_entry:
      new_entry = asset
      new_entry['adgroups'] = [ag_id]
      data.append(new_entry)
      new_entry = {}

  with open(asset_to_ag_json_path, 'w') as f:
    json.dump(data, f, indent=2)


# Central func to create both structure json. both account and asset.
def get_struct(client, account=0):
  """ This function creates a json with 2 structures - account strcut and asset-to-ag struct.
  if an accounts id is given, the account-struct is for that account only.
  if not, its for the whole configured MCC.
  """
  _revert_json()
  total_structure = []
  if account:
    struct = create_account_struct(client,account)
  else:
    struct = create_mcc_struct(client)

  with open(asset_to_ag_json_path, 'r') as f:
    asset_struct = json.load(f)

  structure = {'account_structure': struct, 'asset_structure': asset_struct}
  Service_Class.reset_cid(client)
  return structure


def _revert_json():
  """utility function to revert the json file in each run."""
  clean = []
  with open(asset_to_ag_json_path, 'w') as f:
    json.dump(clean, f, indent=2)

  with open(account_struct_json_path, 'w') as f:
    json.dump(clean, f, indent=2)
