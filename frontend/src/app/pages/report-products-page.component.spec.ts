import { TestBed } from '@angular/core/testing';
import { of } from 'rxjs';

import { ReportProductsPageComponent } from './report-products-page.component';
import { ReportProductService } from '../services/report-product.service';
import { Nr7BuilderService } from '../services/nr7-builder.service';

describe('ReportProductsPageComponent', () => {
  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ReportProductsPageComponent],
      providers: [
        {
          provide: ReportProductService,
          useValue: {
            list: () =>
              of({
                report_products: [
                  {
                    uuid: 'r1',
                    code: 'nba_v1',
                    title: 'NBA',
                    version: 'v1',
                    description: 'NBA shell'
                  }
                ]
              }),
            preview: () =>
              of({
                template: { code: 'nba_v1', title: 'NBA', version: 'v1' },
                payload: {
                  sections: [{ title: 'Executive summary' }],
                  qa: { items: [] },
                  indicator_table: [{ code: 'GBF-H-A1-ZA' }]
                },
                html_preview: '<html></html>',
                run_uuid: 'run-1'
              }),
            exportHtmlUrl: () => '/api/report-products/nba_v1/export.html',
            exportPdfUrl: () => '/api/report-products/nba_v1/export.pdf'
          }
        },
        {
          provide: Nr7BuilderService,
          useValue: {
            listInstances: () =>
              of({
                instances: [
                  {
                    uuid: 'i1',
                    cycle_code: 'CYCLE',
                    cycle_title: 'Cycle',
                    version_label: 'v1',
                    status: 'draft',
                    frozen_at: null,
                    readiness_status: 'not_ready',
                    readiness_score: 0
                  }
                ]
              })
          }
        }
      ]
    }).compileComponents();
  });

  it('renders report products page', async () => {
    const fixture = TestBed.createComponent(ReportProductsPageComponent);
    fixture.detectChanges();
    await fixture.whenStable();
    fixture.detectChanges();
    const compiled = fixture.nativeElement as HTMLElement;
    expect(compiled.textContent).toContain('One Biodiversity Report Products');
  });
});
