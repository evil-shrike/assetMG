/**
 * Copyright 2020 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *      https://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import 'rxjs/add/observable/of';
import 'rxjs/add/operator/catch';
import { BehaviorSubject, Observable } from 'rxjs';
import {
  Asset,
  TextAsset,
  AssetAdGroups,
  AssetConnType,
  AssetType,
  MutateRecord,
} from './../model/asset';
import { UpdateResponse, STATUS } from '../model/response';
import { Account, AccountAGs } from './../model/account';

@Injectable({
  providedIn: 'root',
})
export class AssetService {
  private API_SERVER = 'http://127.0.0.1:5000';

  /** Gets updated when the account changes */
  private _activeAccountId$ = new BehaviorSubject<number>(null);
  private _activeAccount$ = new BehaviorSubject<Account>(null);
  private _accountAGs$ = new BehaviorSubject<AccountAGs>(null);
  private _allAssets$ = new BehaviorSubject<Asset[]>(null);
  private _assetsToAdGroups: Asset[] = [];

  /** Gets updated when an asset is selected */
  private _activeAsset$ = new BehaviorSubject<Asset>(null);
  private _activeAssetAdGroups$ = new BehaviorSubject<AssetAdGroups>(null);

  /** Gets updated when the update Asset is called */
  private _updateFinished$ = new BehaviorSubject<UpdateResponse>(null);

  allAssets$ = this._allAssets$.asObservable();
  activeAccount$ = this._activeAccount$.asObservable();
  activeAccountId$ = this._activeAccountId$.asObservable();
  accountAGs$ = this._accountAGs$.asObservable();
  activeAsset$ = this._activeAsset$.asObservable();
  activeAssetAdGroups$ = this._activeAssetAdGroups$.asObservable();
  updateFinished$ = this._updateFinished$.asObservable();

  constructor(private _http: HttpClient) {}

  private getAllAssets(accountId: number) {
    // Reset the asset observable till the http request is made
    this._allAssets$.next(null);
    // Call the API and update the asset observable
    const endpoint = this.API_SERVER + '/accounts-assets/';
    //let params = new HttpParams().set('cid', accountId?.toString());
    let subscription = this._http
      .get<Asset[]>(endpoint, { params: { cid: accountId?.toString() } })
      .subscribe((assets) => {
        this._allAssets$.next(assets);
        subscription.unsubscribe();
      });
  }

  private getAccountHierarchy(accountId: number) {
    const endpoint = this.API_SERVER + '/structure/';
    //let params = new HttpParams().set('cid', accountId?.toString());
    let subscription = this._http
      .get<Account>(endpoint, { params: { cid: accountId?.toString() } })
      .subscribe((account) => {
        this._activeAccount$.next(account);
        subscription.unsubscribe();
      });
  }

  private getAccountAdGroups(accountId: number) {
    const endpoint = this.API_SERVER + '/account-ag-struct';
    let subscription = this._http
      .get<AccountAGs>(endpoint, { params: { cid: accountId?.toString() } })
      .subscribe((accountAGs) => {
        this._accountAGs$.next(accountAGs);
        subscription.unsubscribe();
      });
  }

  /** Loads all the asset to adgroups mapping */
  private getAssetsToAdGroups() {
    const endpoint = this.API_SERVER + '/assets-to-ag/';
    let subscritpion = this._http.get<Asset[]>(endpoint).subscribe((assets) => {
      this._assetsToAdGroups = assets;
      subscritpion.unsubscribe();
    });
  }

  getAccountIds(): Observable<Account[]> {
    const endpoint = this.API_SERVER + '/accounts/';
    return this._http.get<Account[]>(endpoint);
  }

  loadMccStruct(): Observable<any> {
    const endpoint = this.API_SERVER + '/create-struct/';
    return this._http.get(endpoint);
  }

  changeAsset(asset: Asset) {
    this._activeAsset$.next(asset);
    if (asset) {
      this._activeAssetAdGroups$.next(this.getActiveAssetAdGroups(asset.id));
    } else {
      this._activeAssetAdGroups$.next(null);
    }
  }

  unselectAsset() {
    this.changeAsset(null);
  }

  changeAccount(accountId: number) {
    this._activeAccountId$.next(accountId);
    this.getAllAssets(accountId);
    //this.getAccountHierarchy(accountId);
    this.getAccountAdGroups(accountId);
    this.getAssetsToAdGroups();
    this.changeAsset(null);
  }

  getActiveAssetAdGroups(assetId: number) {
    let assetAdGroups: AssetAdGroups = new Map();
    this._assetsToAdGroups.filter(function (asset) {
      if (asset.id == assetId) {
        let AssetConnection = AssetConnType.ADGROUP;
        if (asset.type == AssetType.TEXT) {
          (asset as TextAsset).text_type.toLowerCase() ==
          AssetConnType.HEADLINE.toLowerCase()
            ? (AssetConnection = AssetConnType.HEADLINE)
            : (AssetConnection = AssetConnType.DESC);
        }
        assetAdGroups.set(AssetConnection, asset.adgroups);
      }
    });
    return assetAdGroups;
  }

  updateAsset(changedAsset: Asset, updateArray: MutateRecord[]) {
    const endpoint = this.API_SERVER + '/mutate-ad/';
    let subscritpion = this._http
      .post(endpoint, updateArray, { observe: 'response' })
      .subscribe(
        (response) => {
          // update the asset to adgroup cache
          let updatedAssets: Asset[] = [];
          for (let update of <any[]>response.body) {
            updatedAssets.push(update.asset);
            if (update.index) {
              // This is a non-text asset
              this._assetsToAdGroups[update.index] = update.asset;
            } else if (update.asset?.length) {
              // Text asset, so index can be {found in the assets array (headlines and descriptions)
              for (let txt_asset of update.asset) {
                if (txt_asset.index) {
                  this._assetsToAdGroups[txt_asset.index] = txt_asset.asset;
                } else {
                  this._assetsToAdGroups.push(txt_asset.asset);
                }
              }
            } else {
              this._assetsToAdGroups.push(update.asset);
            }
          }
          // Update the new selection
          this._activeAssetAdGroups$.next(
            this.getActiveAssetAdGroups(changedAsset.id)
          );
          // Updated the caller that the API is done
          let msg = '';
          if (response.status === STATUS.PARTIAL_SUCCESS) {
            let failures =
              (<any[]>response.body)[0].failures ||
              (<any>response.body).failures;
            if (failures) {
              for (let failure of failures) {
                msg += `Update failed for the ad group ${failure.adgroup}:
                    ${failure.error_message}<br/>`;
              }
            } else {
              msg = 'Update failed for some ad groups.';
            }
          }
          this._updateFinished$.next({
            status_code: response.status,
            msg: msg,
            assets: updatedAssets,
          });
          subscritpion.unsubscribe();
        },
        (error) => {
          // API call failed - Returned status 500
          let errorMessage = '';
          let failures = error.error[0]?.failures || error.error?.failures;
          if (failures) {
            for (let failure of failures) {
              errorMessage += `Update failed for the ad group ${failure.adgroup}: ${failure.error_message}<br/>`;
            }
          } else {
            errorMessage = `Error Code: ${error.status}<br/>Message: ${error.message}`;
          }

          this._updateFinished$.next({
            status_code: STATUS.FAIL,
            msg: errorMessage,
            assets: [],
          });
          subscritpion.unsubscribe();
        }
      );
  }

  addNewAsset(asset: Asset) {
    // Update all assets with the newly uploaded asset
    if (asset) {
      console.log('Asset: ', asset);
      let waitTime = 0;
      if (asset.type == AssetType.IMG) {
        waitTime = 12000;
      }
      this._assetsToAdGroups.push(asset);
      // This is a workaround to overcome the server not detecting the image
      // type and loading it - so we give it some time.
      setTimeout(() => {
        this._allAssets$.next(this._allAssets$.getValue().concat(asset));
      }, waitTime);
    }
  }
}
