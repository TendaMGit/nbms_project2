import { TestBed } from '@angular/core/testing';
import { of } from 'rxjs';

import { ReportingPageComponent } from './reporting-page.component';
import { NationalReportService } from '../services/national-report.service';
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
                    cycle_code: 'NR7',
                    cycle_title: 'National Report 7',
                    version_label: 'v1',
                    status: 'draft',
                    frozen_at: null,
                    readiness_status: 'warning',
                    readiness_score: 55
                  }
                ]
              })
          }
        },
        {
          provide: NationalReportService,
          useValue: {
            workspace: () =>
              of({
                instance: {
                  uuid: '00000000-0000-0000-0000-000000000001',
                  cycle_code: 'NR7',
                  cycle_title: 'National Report 7',
                  version_label: 'v1',
                  report_title: 'South Africa NR7',
                  country_name: 'South Africa',
                  status: 'draft',
                  is_public: false,
                  focal_point_org: 'SANBI',
                  publishing_authority_org: 'DFFE',
                  finalized_at: null,
                  final_content_hash: ''
                },
                pack: { code: 'cbd_national_report_v1', title: 'CBD National Report', version: 'v1' },
                sections: [
                  {
                    uuid: 's1',
                    section_code: 'section-i',
                    section_title: 'Section I - Process Overview',
                    ordering: 1,
                    response_json: { country_name: 'South Africa' },
                    current_version: 1,
                    current_content_hash: 'abc',
                    locked_for_editing: false,
                    updated_by: 'staff',
                    updated_at: '2026-02-09T00:00:00Z',
                    latest_revision_uuid: 'r1'
                  }
                ],
                section_approvals: [{ section_code: 'section-i', approved: false, approved_by: null, approved_at: null }],
                workflow: {
                  uuid: 'wf1',
                  status: 'active',
                  current_step: 'draft',
                  locked: false,
                  latest_content_hash: '',
                  actions: []
                },
                validation: { overall_ready: false, generated_at: '2026-01-01T00:00:00Z', qa_items: [], sections: [] },
                preview_payload: { schema: 'nbms.cbd_national_report.v1' },
                latest_dossier: null,
                capabilities: {}
              }),
            section: () =>
              of({
                uuid: 's1',
                section_code: 'section-i',
                section_title: 'Section I - Process Overview',
                ordering: 1,
                response_json: { country_name: 'South Africa' },
                current_version: 1,
                current_content_hash: 'abc',
                locked_for_editing: false,
                updated_by: 'staff',
                updated_at: '2026-02-09T00:00:00Z',
                latest_revision_uuid: 'r1',
                schema_json: {
                  fields: [{ key: 'country_name', label: 'Country name', type: 'text', required: true }]
                }
              }),
            sectionHistory: () =>
              of({
                section_code: 'section-i',
                current_version: 1,
                revisions: [],
                diff: null
              }),
            comments: () => of({ threads: [] }),
            suggestions: () => of({ suggestions: [] }),
            saveSection: () => of({}),
            workflowAction: () => of({}),
            generateSectionIiiSkeleton: () => of({}),
            recomputeSectionIvRollup: () => of({}),
            generateDossier: () => of({}),
            addComment: () => of({ threads: [] }),
            updateCommentThreadStatus: () => of({}),
            decideSuggestion: () => of({}),
            exportPdfUrl: () => '/api/reports/x/export.pdf',
            exportDocxUrl: () => '/api/reports/x/export.docx',
            exportJsonUrl: () => '/api/reports/x/export',
            latestDossierDownloadUrl: () => '/api/reports/x/dossier/latest?download=1'
          }
        }
      ]
    }).compileComponents();
  });

  it('renders National Report Workspace shell', async () => {
    const fixture = TestBed.createComponent(ReportingPageComponent);
    fixture.detectChanges();
    await fixture.whenStable();
    fixture.detectChanges();
    const compiled = fixture.nativeElement as HTMLElement;
    expect(compiled.textContent).toContain('National Report Workspace');
    expect(compiled.textContent).toContain('Sections');
    expect(compiled.textContent).toContain('Review & QA');
  });
});
