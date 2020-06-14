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

"""setup module for the assetMG tool.

setting up both api config yaml files(googleads.yaml & google-ads.yaml)
with the paramaters given by the user in the config.yaml file
"""

import yaml
import os


def set_api_configs():
  """set API configuration files."""

  with open('../../config.yaml', 'r') as f:
    config = yaml.load(f, Loader=yaml.FullLoader)

  aw_config = {'adwords': config}
  with open('../config/googleads.yaml', 'w') as f:
    yaml.dump(aw_config, f)

  config['login_customer_id'] = config['client_customer_id']
  with open('../config/google-ads.yaml', 'w') as f:
    yaml.dump(config, f)


