import { TestBed } from '@angular/core/testing';
import { of } from 'rxjs';
import { MatSnackBar } from '@angular/material/snack-bar';
import { Router } from '@angular/router';

import { TemplatePacksPageComponent } from './template-packs-page.component';
import { DownloadRecordService } from '../services/download-record.service';
import { TemplatePackService } from '../services/template-pack.service';
import { Nr7BuilderService } from '../services/nr7-builder.service';

describe('TemplatePacksPageComponent', () => {
  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [TemplatePacksPageComponent],
      providers: [
        {
          provide: TemplatePackService,
          useValue: {
            list: () =>
              of({
                packs: [
                  {
                    uuid: '1',
                    code: 'ramsar_v1',
                    title: 'Ramsar',
                    mea_code: 'RAMSAR',
                    version: 'v1',
                    description: 'Ramsar pack',
                    section_count: 4
                  }
                ]
              }),
            sections: () =>
              of({
                pack: { code: 'ramsar_v1', title: 'Ramsar', mea_code: 'RAMSAR', version: 'v1' },
                sections: [
                  {
                    uuid: 's1',
                    code: 'section_1_institutional',
                    title: 'Section 1',
                    ordering: 1,
                    schema_json: { fields: [{ key: 'reporting_party', label: 'Reporting party', type: 'text' }] }
                  }
                ]
              }),
            responses: () =>
              of({
                pack: { code: 'ramsar_v1' },
                responses: [
                  {
                    section_code: 'section_1_institutional',
                    section_title: 'Section 1',
                    response_json: { reporting_party: 'South Africa' },
                    updated_by: 'staff',
                    updated_at: null
                  }
                ]
              }),
            saveResponse: () => of({ section_code: 'section_1_institutional', response_json: {} }),
            validate: () =>
              of({
                pack_code: 'ramsar_v1',
                instance_uuid: 'i1',
                generated_at: '2026-02-07T00:00:00Z',
                overall_ready: true,
                qa_items: [],
                sections: []
              }),
            exportPdfUrl: () => '/api/template-packs/ramsar_v1/instances/i1/export.pdf'
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
        },
        { provide: MatSnackBar, useValue: { open: () => undefined } },
        {
          provide: DownloadRecordService,
          useValue: {
            create: () =>
              of({
                uuid: 'dl-1',
                landing_url: '/downloads/dl-1',
                record: {}
              })
          }
        },
        {
          provide: Router,
          useValue: { navigate: () => Promise.resolve(true) }
        }
      ]
    }).compileComponents();
  });

  it('renders template pack workspace', async () => {
    const fixture = TestBed.createComponent(TemplatePacksPageComponent);
    fixture.detectChanges();
    await fixture.whenStable();
    fixture.detectChanges();
    const compiled = fixture.nativeElement as HTMLElement;
    expect(compiled.textContent).toContain('MEA Template Packs');
    expect(compiled.textContent).toContain('Section 1');
  });
});
