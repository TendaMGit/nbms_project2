import { Routes } from '@angular/router';
import { BirdieProgrammePageComponent } from './pages/birdie-programme-page.component';
import { DashboardPageComponent } from './pages/dashboard-page.component';
import { IndicatorDetailPageComponent } from './pages/indicator-detail-page.component';
import { IndicatorExplorerPageComponent } from './pages/indicator-explorer-page.component';
import { MapViewerPageComponent } from './pages/map-viewer-page.component';
import { ProgrammeOpsPageComponent } from './pages/programme-ops-page.component';
import { ReportProductsPageComponent } from './pages/report-products-page.component';
import { ReportingPageComponent } from './pages/reporting-page.component';
import { SystemHealthPageComponent } from './pages/system-health-page.component';
import { TemplatePacksPageComponent } from './pages/template-packs-page.component';
import { requireCapability } from './guards/capability.guard';

export const routes: Routes = [
  { path: '', pathMatch: 'full', redirectTo: 'dashboard' },
  {
    path: 'dashboard',
    component: DashboardPageComponent,
    canActivate: [requireCapability('can_view_dashboard')],
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
    canActivate: [requireCapability('can_view_spatial')],
    data: { title: 'Spatial Viewer', sectionKey: 'section_iv' }
  },
  {
    path: 'programmes',
    component: ProgrammeOpsPageComponent,
    canActivate: [requireCapability('can_view_programmes')],
    data: { title: 'Programme Operations', sectionKey: 'section_iii' }
  },
  {
    path: 'programmes/birdie',
    component: BirdieProgrammePageComponent,
    canActivate: [requireCapability('can_view_birdie')],
    data: { title: 'BIRDIE Dashboard', sectionKey: 'section_iii' }
  },
  {
    path: 'nr7-builder',
    component: ReportingPageComponent,
    canActivate: [requireCapability('can_view_reporting_builder')],
    data: { title: 'NR7 Report Builder', sectionKey: 'section_v' }
  },
  {
    path: 'template-packs',
    component: TemplatePacksPageComponent,
    canActivate: [requireCapability('can_view_template_packs')],
    data: { title: 'MEA Template Packs', sectionKey: 'section_ii' }
  },
  {
    path: 'system-health',
    component: SystemHealthPageComponent,
    canActivate: [requireCapability('can_view_system_health')],
    data: { title: 'System Health', sectionKey: 'section_i' }
  },
  {
    path: 'report-products',
    component: ReportProductsPageComponent,
    canActivate: [requireCapability('can_view_report_products')],
    data: { title: 'Report Products', sectionKey: 'section_v' }
  }
];
