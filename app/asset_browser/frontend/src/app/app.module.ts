import { BrowserModule } from '@angular/platform-browser';
import { NgModule } from '@angular/core';

import { AppRoutingModule } from './app-routing.module';
import { AppComponent } from './app.component';
import { AssetGalleryComponent } from './asset-gallery/asset-gallery.component';
import { AssetDetailsComponent } from './asset-details/asset-details.component';
import { AssetComponent } from './asset/asset.component';

import { MaterialModule } from './shared/material.module';
import { BrowserAnimationsModule } from '@angular/platform-browser/animations';
import { AccountCampaignsComponent } from './account-campaigns/account-campaigns.component';

@NgModule({
  declarations: [
    AppComponent,
    AssetGalleryComponent,
    AssetDetailsComponent,
    AssetComponent,
    AccountCampaignsComponent,
  ],
  imports: [
    BrowserModule,
    AppRoutingModule,
    MaterialModule,
    BrowserAnimationsModule,
  ],
  providers: [],
  bootstrap: [AppComponent],
})
export class AppModule {}
