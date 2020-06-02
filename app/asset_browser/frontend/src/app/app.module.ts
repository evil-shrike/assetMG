import { BrowserModule } from '@angular/platform-browser';
import { NgModule } from '@angular/core';
import { HttpClientModule } from '@angular/common/http';
import { BrowserAnimationsModule } from '@angular/platform-browser/animations';
import { AppRoutingModule } from './app-routing.module';
import { AppComponent } from './app.component';
import { MaterialModule } from './shared/material.module';
import { HTTP_INTERCEPTORS } from '@angular/common/http';
import { FormsModule } from '@angular/forms';

import { AssetGalleryComponent } from './asset-gallery/asset-gallery.component';
import { AssetDetailsComponent } from './asset-details/asset-details.component';
import { AssetComponent } from './asset/asset.component';
import { AccountCampaignsComponent } from './account-campaigns/account-campaigns.component';
import { ToolbarComponent } from './toolbar/toolbar.component';
import { LoaderComponent } from './shared/loader/loader.component';
import { LoaderService } from './services/loader.service';
import { LoaderInterceptor } from './interceptors/loader.interceptor';
import { HttpErrorInterceptor } from './interceptors/http-error.interceptor';
import { SearchBarComponent } from './search-bar/search-bar.component';
import { ProgressBtnComponent } from './shared/progress-btn/progress-btn.component';

@NgModule({
  declarations: [
    AppComponent,
    AssetGalleryComponent,
    AssetDetailsComponent,
    AssetComponent,
    AccountCampaignsComponent,
    ToolbarComponent,
    LoaderComponent,
    SearchBarComponent,
    ProgressBtnComponent,
  ],
  imports: [
    BrowserModule,
    AppRoutingModule,
    MaterialModule,
    BrowserAnimationsModule,
    HttpClientModule,
    FormsModule,
  ],
  providers: [
    LoaderService,
    { provide: HTTP_INTERCEPTORS, useClass: LoaderInterceptor, multi: true },
    { provide: HTTP_INTERCEPTORS, useClass: HttpErrorInterceptor, multi: true },
  ],
  bootstrap: [AppComponent],
})
export class AppModule {}
