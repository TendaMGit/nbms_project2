import { Routes } from '@angular/router';
import { DashboardPageComponent } from './pages/dashboard-page.component';
import { IndicatorDetailPageComponent } from './pages/indicator-detail-page.component';
import { IndicatorExplorerPageComponent } from './pages/indicator-explorer-page.component';
import { MapViewerPageComponent } from './pages/map-viewer-page.component';
import { ReportingPageComponent } from './pages/reporting-page.component';
import { SystemHealthPageComponent } from './pages/system-health-page.component';
import { TemplatePacksPageComponent } from './pages/template-packs-page.component';

export const routes: Routes = [
  { path: '', pathMatch: 'full', redirectTo: 'dashboard' },
  {
    path: 'dashboard',
    component: DashboardPageComponent,
    data: { title: 'Dashboard', sectionKey: 'section_i' }
  },
  {
    path: 'indicators',
    component: IndicatorExplorerPageComponent,
    data: { title: 'Indicator Explorer', sectionKey: 'section_iii' }
  },
  {
    path: 'indicators/:uuid',
    component: IndicatorDetailPageComponent,
    data: { title: 'Indicator Detail', sectionKey: 'section_iii' }
  },
  {
    path: 'map',
    component: MapViewerPageComponent,
    data: { title: 'Spatial Viewer', sectionKey: 'section_iv' }
  },
  {
    path: 'nr7-builder',
    component: ReportingPageComponent,
    data: { title: 'NR7 Report Builder', sectionKey: 'section_v' }
  },
  {
    path: 'template-packs',
    component: TemplatePacksPageComponent,
    data: { title: 'MEA Template Packs', sectionKey: 'section_ii' }
  },
  {
    path: 'system-health',
    component: SystemHealthPageComponent,
    data: { title: 'System Health', sectionKey: 'section_i' }
  }
];
