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

"""This module allows uploading new assets to a google ads account.

This module allows uploading assets threw the assetMG tool, and assigning them
to a list of adgroups utilaizing the mutate module.
"""

import app.backend.mutate as mutate
from app.backend.structure import get_assets_from_adgroup
from app.backend.service import Service_Class
from app.backend.error_handling import error_mapping
from pathlib import Path
import urllib
import json


asset_to_ag_json_path = Path('app/cache/asset_to_ag.json')
yt_thumbnail_url = 'https://img.youtube.com/vi/%s/1.jpg'


def upload_html5_asset(
    client, googleads_client, account, asset_name, path, adgroups):
  """Upload html5 asset and assign to ad groups if given."""
  asset_service = Service_Class.get_asset_service(client)

  with open(path, 'rb') as html_handle:
    html_data = html_handle.read()

  media_bundle_asset = {
      'xsi_type': 'MediaBundleAsset',
      'assetName': asset_name,
      'mediaBundleData': html_data
  }
  operation = {'operator': 'ADD', 'operand': media_bundle_asset}

  asset = asset_service.mutate([operation])['value'][0]

  new_asset = {
      'id': asset['assetId'],
      'name': asset['assetName'],
      'type': 'MEDIA_BUNDLE',
  }

  return _assign_new_asset_to_adgroups(
      client, googleads_client, account, new_asset, adgroups)


def upload_yt_video_asset(
    client, googleads_client, account, asset_name, url, adgroups):
  """Upload YT video asset and assign to ad groups if given."""
  asset_service = Service_Class.get_asset_service(client)

  url_data = urllib.parse.urlparse(url)
  if url_data.netloc == 'youtu.be':
    video_id = url_data.path.lstrip('/')
  else:
    query = urllib.parse.parse_qs(url_data.query)
    video_id = query['v'][0]

  vid_asset = {
      'xsi_type': 'YouTubeVideoAsset',
      'assetName': asset_name,
      'youTubeVideoId': video_id
  }

  operation = {'operator': 'ADD', 'operand': vid_asset}

  asset = asset_service.mutate([operation])['value'][0]

  new_asset = {
      'id': asset['assetId'],
      'name': asset['assetName'],
      'type': 'YOUTUBE_VIDEO',
      'video_id': video_id,
      'link': url,
      'image_url': yt_thumbnail_url%(video_id)
  }

  return _assign_new_asset_to_adgroups(
      client, googleads_client, account, new_asset, adgroups)


def upload_image_asset(
    client, googleads_client, account, asset_name, path, adgroups):
  """Upload image asset and assign to ad groups if given."""
  asset_service = Service_Class.get_asset_service(client)

  with open(path, 'rb') as image_handle:
    image_data = image_handle.read()

  # Construct media and upload image asset.
  image_asset = {
      'xsi_type': 'ImageAsset',
      'assetName': asset_name,
      'imageData': image_data,
  }

  operation = {'operator': 'ADD', 'operand': image_asset}

  asset = asset_service.mutate([operation])['value'][0]

  new_asset = {
      'id': asset['assetId'],
      'name': asset['assetName'],
      'type': 'IMAGE',
      'image_url': asset['fullSizeInfo']['imageUrl']
  }

  return _assign_new_asset_to_adgroups(
      client, googleads_client, account, new_asset, adgroups)


def upload_text_asset(
    client, googleads_client, account, text_type, name, text, adgroups):
  """Upload text asset and assign to ad groups."""
  asset = {
      'id': None,
      'name': name,
      'type': 'TEXT',
      'text_type': text_type,
      'asset_text': text
  }

  return _assign_new_asset_to_adgroups(
      client, googleads_client, account, asset, adgroups, text_type)


def _assign_new_asset_to_adgroups(client, googleads_client, account, asset,
                                  adgroups, text_type='descriptions'):
  """Assigns the new asset uploaded to the given ad groups, using the mutate
  module."""
  # common_typos_disable
  successeful_assign = []
  unsuccesseful_assign = []
  asset['adgroups'] = []

  if not adgroups:
    return {'asset': asset, 'status': -1}

  for ag in adgroups:
    # mutate_ad returns None if it finishes succesfully
    try:
      mutate.mutate_ad(client, account, ag, asset, 'ADD', text_type)
      successeful_assign.append({"id": ag})
    except Exception as e:
      unsuccesseful_assign.append({
          'adgroup': ag,
          'error_message': error_mapping(str(e)), 'err': str(e)
      })
  # assignment status:
  #   0 - succesfull,
  #   1 - partialy succesfull,
  #   2 - unsuccesfull,
  #  -1 - no adgroups to assign
  status = 2

  # if successfully assigend only to some ad groups
  if successeful_assign and unsuccesseful_assign:
    status = 1

  # if successefully assigned to all ad groups
  elif successeful_assign:
    status = 0

  # if text assets aren't assigned to any adgroup they weren't uploaded
  if asset['type'] == 'TEXT' and status == 2:
    return {
        'status': 3,
        'unsuccessfull': unsuccesseful_assign
    }

  if asset['type'] == 'TEXT' and successeful_assign:
    asset = _extract_text_asset_info(
        googleads_client, account, asset, successeful_assign[0])

  asset['adgroups'] = successeful_assign
  _update_asset_struct(asset)

  return {
      'asset': asset,
      'status': status,
      'successfull': successeful_assign,
      'unsuccessfull': unsuccesseful_assign
  }


def _update_asset_struct(asset):
  """Update the asset_to_ag file with the new assets and their adgroups"""
  with open(asset_to_ag_json_path, 'r') as f:
    struct = json.load(f)

  struct.append(asset)

  with open(asset_to_ag_json_path, 'w') as f:
    json.dump(struct, f, indent=2)


def _extract_text_asset_info(googleads_client, account, thin_asset, adgroup):
  """Retrive text-assets info from an adgroup it was assigned to"""
  adgroups_assets = get_assets_from_adgroup(googleads_client, account, adgroup["id"])

  for asset in adgroups_assets:
    if asset['type'] == 'TEXT':
      if (asset['asset_text'] == thin_asset['asset_text']
          and asset['text_type'] == thin_asset['text_type']):
        return asset


def upload(client,
           googleads_client,
           account,
           asset_type,
           asset_name,
           asset_text='',
           path='',
           url='',
           adgroups=[]):
  """Central function. Routes to the relevant function based on the asset type.

  Args:
    client : adwords api client.
    account : account id, to which the asset will be uploaded.
    asset_type : image,video,text,html5. The relevant upload func is triggered
    according to the type.
    asset_name : name to assign to the asset. has to be unique.
    asset_text : for text assets. Text assets must be assigned to at least one
    adgroup inorder to upload.
    path : for image and html5 assets. path the file on the users computer.
    url : for YT videos.,
    adgroups : a list of adgroups to assign the asset to.
  Returns:
    exit code
    exit message
  """
  client.SetClientCustomerId(account)

  if asset_type == 'IMAGE':
    return upload_image_asset(
        client, googleads_client, account, asset_name, path, adgroups)

  if asset_type in ['descriptions', 'headlines']:
    return upload_text_asset(client, googleads_client, account, asset_type,
                             asset_name, asset_text, adgroups)

  if asset_type == 'YOUTUBE_VIDEO':
    return upload_yt_video_asset(
        client, googleads_client, account, asset_name, url, adgroups)

  if asset_type == 'MEDIA_BUNDLE':
    return upload_html5_asset(
        client, googleads_client, account, asset_name, path, adgroups)

