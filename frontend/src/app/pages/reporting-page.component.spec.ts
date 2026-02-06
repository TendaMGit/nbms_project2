import { TestBed } from '@angular/core/testing';
import { of } from 'rxjs';

import { ReportingPageComponent } from './reporting-page.component';
import { Nr7BuilderService } from '../services/nr7-builder.service';

describe('ReportingPageComponent', () => {
  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ReportingPageComponent],
      providers: [
        {
          provide: Nr7BuilderService,
          useValue: {
            listInstances: () =>
              of({
                instances: [
                  {
                    uuid: '00000000-0000-0000-0000-000000000001',
                    cycle_code: 'CYCLE',
                    cycle_title: 'Cycle',
                    version_label: 'v1',
                    status: 'draft',
                    frozen_at: null,
                    readiness_status: 'warning',
                    readiness_score: 55
                  }
                ]
              }),
            getSummary: () =>
              of({
                instance: {
                  uuid: '00000000-0000-0000-0000-000000000001',
                  cycle_code: 'CYCLE',
                  cycle_title: 'Cycle',
                  version_label: 'v1',
                  status: 'draft',
                  frozen_at: null
                },
                validation: {
                  overall_ready: false,
                  generated_at: '2026-01-01T00:00:00Z',
                  qa_items: [
                    { severity: 'BLOCKER', code: 'missing_field', section: 'section-i', message: 'Missing field' }
                  ],
                  sections: [
                    {
                      code: 'section-i',
                      title: 'Section I',
                      required: true,
                      state: 'draft',
                      completion: 45,
                      missing_fields: ['contact_email'],
                      incomplete_fields: []
                    }
                  ]
                },
                preview_payload: { schema: 'nbms.ort.nr7.v2' },
                preview_error: null,
                links: {
                  section_i: '/reporting/instances/00000000-0000-0000-0000-000000000001/section-i/'
                }
              }),
            getPdfUrl: () => '/api/reporting/instances/00000000-0000-0000-0000-000000000001/nr7/export.pdf'
          }
        }
      ]
    }).compileComponents();
  });

  it('renders NR7 Report Builder shell', async () => {
    const fixture = TestBed.createComponent(ReportingPageComponent);
    fixture.detectChanges();
    await fixture.whenStable();
    fixture.detectChanges();
    await fixture.whenStable();
    const compiled = fixture.nativeElement as HTMLElement;
    expect(compiled.textContent).toContain('NR7 Report Builder');
    expect(compiled.textContent).toContain('Sections I-V');
    expect(compiled.textContent).toContain('QA Findings');
  });
});
