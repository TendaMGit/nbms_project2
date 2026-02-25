import { Routes } from '@angular/router';
import { requireCapability } from './guards/capability.guard';

export const routes: Routes = [
  { path: '', pathMatch: 'full', redirectTo: 'dashboard' },

  {
    path: 'dashboard',
    loadComponent: () =>
      import('./pages/dashboard-page.component').then((m) => m.DashboardPageComponent),
    canActivate: [requireCapability('can_view_dashboard')],
    data: { title: 'Dashboard', sectionKey: 'section_i' }
  },
  {
    path: 'work',
    loadComponent: () =>
      import('./pages/work-page.component').then((m) => m.WorkPageComponent),
    canActivate: [requireCapability('can_view_dashboard')],
    data: { title: 'My Work', sectionKey: 'section_i' }
  },
  {
    path: 'account/preferences',
    loadComponent: () =>
      import('./pages/account-preferences-page.component').then((m) => m.AccountPreferencesPageComponent),
    canActivate: [requireCapability('can_view_dashboard')],
    data: { title: 'Preferences', sectionKey: 'section_i' }
  },
  {
    path: 'indicators',
    loadComponent: () =>
      import('./pages/indicator-explorer-page.component').then((m) => m.IndicatorExplorerPageComponent),
    data: { title: 'Indicator Explorer', sectionKey: 'section_iii' }
  },
  {
    path: 'indicators/:uuid',
    loadComponent: () =>
      import('./pages/indicator-detail-page.component').then((m) => m.IndicatorDetailPageComponent),
    data: { title: 'Indicator Detail', sectionKey: 'section_iii' }
  },

  {
    path: 'reporting',
    loadComponent: () =>
      import('./pages/reporting-page.component').then((m) => m.ReportingPageComponent),
    canActivate: [requireCapability('can_view_reporting_builder')],
    data: { title: 'Reporting Workspace', sectionKey: 'section_v' }
  },
  {
    path: 'reports/:uuid',
    loadComponent: () =>
      import('./pages/reporting-page.component').then((m) => m.ReportingPageComponent),
    canActivate: [requireCapability('can_view_reporting_builder')],
    data: { title: 'Report Workspace', sectionKey: 'section_v' }
  },
  {
    path: 'nr7-builder',
    pathMatch: 'full',
    redirectTo: 'reporting'
  },

  {
    path: 'template-packs',
    loadComponent: () =>
      import('./pages/template-packs-page.component').then((m) => m.TemplatePacksPageComponent),
    canActivate: [requireCapability('can_view_template_packs')],
    data: { title: 'Template Packs', sectionKey: 'section_ii' }
  },
  {
    path: 'template-packs/:pack_code',
    loadComponent: () =>
      import('./pages/template-packs-page.component').then((m) => m.TemplatePacksPageComponent),
    canActivate: [requireCapability('can_view_template_packs')],
    data: { title: 'Template Pack Detail', sectionKey: 'section_ii' }
  },

  {
    path: 'registries',
    loadComponent: () =>
      import('./pages/coming-soon-page.component').then((m) => m.ComingSoonPageComponent),
    canActivate: [requireCapability('can_view_registries')],
    data: {
      title: 'Registries',
      sectionKey: 'section_iv',
      description:
        'Registry home is being redesigned with unified explorer patterns for Taxa, IAS, and Ecosystems.',
      fallbackRoute: '/registries/taxa'
    }
  },
  {
    path: 'registries/ecosystems',
    loadComponent: () =>
      import('./pages/ecosystem-registry-page.component').then((m) => m.EcosystemRegistryPageComponent),
    canActivate: [requireCapability('can_view_registries')],
    data: { title: 'Ecosystem Registry', sectionKey: 'section_iv' }
  },
  {
    path: 'registries/taxa',
    loadComponent: () =>
      import('./pages/taxon-registry-page.component').then((m) => m.TaxonRegistryPageComponent),
    canActivate: [requireCapability('can_view_registries')],
    data: { title: 'Taxon Registry', sectionKey: 'section_iv' }
  },
  {
    path: 'registries/ias',
    loadComponent: () =>
      import('./pages/ias-registry-page.component').then((m) => m.IasRegistryPageComponent),
    canActivate: [requireCapability('can_view_registries')],
    data: { title: 'IAS Registry', sectionKey: 'section_iv' }
  },

  {
    path: 'spatial/map',
    loadComponent: () =>
      import('./pages/map-viewer-page.component').then((m) => m.MapViewerPageComponent),
    canActivate: [requireCapability('can_view_spatial')],
    data: { title: 'Spatial Viewer', sectionKey: 'section_iv' }
  },
  {
    path: 'spatial/layers',
    loadComponent: () =>
      import('./pages/coming-soon-page.component').then((m) => m.ComingSoonPageComponent),
    canActivate: [requireCapability('can_view_spatial')],
    data: {
      title: 'Spatial Layers',
      sectionKey: 'section_iv',
      description: 'Spatial layer registry is being upgraded with upload validation and ingestion history.',
      fallbackRoute: '/spatial/map'
    }
  },
  {
    path: 'map',
    pathMatch: 'full',
    redirectTo: 'spatial/map'
  },

  {
    path: 'programmes',
    loadComponent: () =>
      import('./pages/programme-ops-page.component').then((m) => m.ProgrammeOpsPageComponent),
    canActivate: [requireCapability('can_view_programmes')],
    data: { title: 'Programme Operations', sectionKey: 'section_iii' }
  },
  {
    path: 'programmes/templates',
    loadComponent: () =>
      import('./pages/programme-templates-page.component').then((m) => m.ProgrammeTemplatesPageComponent),
    canActivate: [requireCapability('can_manage_programme_templates')],
    data: { title: 'Programme Templates', sectionKey: 'section_iii' }
  },
  {
    path: 'programmes/birdie',
    loadComponent: () =>
      import('./pages/birdie-programme-page.component').then((m) => m.BirdieProgrammePageComponent),
    canActivate: [requireCapability('can_view_birdie')],
    data: { title: 'BIRDIE Dashboard', sectionKey: 'section_iii' }
  },
  {
    path: 'integrations',
    loadComponent: () =>
      import('./pages/birdie-programme-page.component').then((m) => m.BirdieProgrammePageComponent),
    canActivate: [requireCapability('can_view_birdie')],
    data: { title: 'Integrations', sectionKey: 'section_iii' }
  },

  {
    path: 'downloads',
    loadComponent: () =>
      import('./pages/report-products-page.component').then((m) => m.ReportProductsPageComponent),
    canActivate: [requireCapability('can_view_report_products')],
    data: { title: 'Downloads Center', sectionKey: 'section_v' }
  },
  {
    path: 'report-products',
    loadComponent: () =>
      import('./pages/report-products-page.component').then((m) => m.ReportProductsPageComponent),
    canActivate: [requireCapability('can_view_report_products')],
    data: { title: 'Report Products', sectionKey: 'section_v' }
  },

  {
    path: 'admin',
    loadComponent: () =>
      import('./pages/coming-soon-page.component').then((m) => m.ComingSoonPageComponent),
    canActivate: [requireCapability('can_view_system_health')],
    data: {
      title: 'Admin',
      sectionKey: 'section_i',
      description:
        'Admin workspace modernization is in progress. Use Django admin for full operations in the meantime.',
      fallbackRoute: '/system/health'
    }
  },
  {
    path: 'system/health',
    loadComponent: () =>
      import('./pages/system-health-page.component').then((m) => m.SystemHealthPageComponent),
    canActivate: [requireCapability('can_view_system_health')],
    data: { title: 'System Health', sectionKey: 'section_i' }
  },
  {
    path: 'system-health',
    pathMatch: 'full',
    redirectTo: 'system/health'
  }
];
