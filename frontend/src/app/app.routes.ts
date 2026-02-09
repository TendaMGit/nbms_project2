import { Routes } from '@angular/router';
import { BirdieProgrammePageComponent } from './pages/birdie-programme-page.component';
import { DashboardPageComponent } from './pages/dashboard-page.component';
import { EcosystemRegistryPageComponent } from './pages/ecosystem-registry-page.component';
import { IasRegistryPageComponent } from './pages/ias-registry-page.component';
import { IndicatorDetailPageComponent } from './pages/indicator-detail-page.component';
import { IndicatorExplorerPageComponent } from './pages/indicator-explorer-page.component';
import { MapViewerPageComponent } from './pages/map-viewer-page.component';
import { ProgrammeOpsPageComponent } from './pages/programme-ops-page.component';
import { ProgrammeTemplatesPageComponent } from './pages/programme-templates-page.component';
import { ReportProductsPageComponent } from './pages/report-products-page.component';
import { ReportingPageComponent } from './pages/reporting-page.component';
import { SystemHealthPageComponent } from './pages/system-health-page.component';
import { TaxonRegistryPageComponent } from './pages/taxon-registry-page.component';
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
    path: 'programmes/templates',
    component: ProgrammeTemplatesPageComponent,
    canActivate: [requireCapability('can_manage_programme_templates')],
    data: { title: 'Programme Templates', sectionKey: 'section_iii' }
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
    data: { title: 'National Report Workspace', sectionKey: 'section_v' }
  },
  {
    path: 'template-packs',
    component: TemplatePacksPageComponent,
    canActivate: [requireCapability('can_view_template_packs')],
    data: { title: 'MEA Template Packs', sectionKey: 'section_ii' }
  },
  {
    path: 'registries/ecosystems',
    component: EcosystemRegistryPageComponent,
    canActivate: [requireCapability('can_view_registries')],
    data: { title: 'Ecosystem Registry', sectionKey: 'section_iv' }
  },
  {
    path: 'registries/taxa',
    component: TaxonRegistryPageComponent,
    canActivate: [requireCapability('can_view_registries')],
    data: { title: 'Taxon Registry', sectionKey: 'section_iv' }
  },
  {
    path: 'registries/ias',
    component: IasRegistryPageComponent,
    canActivate: [requireCapability('can_view_registries')],
    data: { title: 'IAS Registry', sectionKey: 'section_iv' }
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
