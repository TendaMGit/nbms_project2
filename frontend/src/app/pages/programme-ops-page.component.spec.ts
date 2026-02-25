import { TestBed } from '@angular/core/testing';
import { of } from 'rxjs';
import { MatSnackBar } from '@angular/material/snack-bar';
import { Router } from '@angular/router';

import { ProgrammeOpsPageComponent } from './programme-ops-page.component';
import { DownloadRecordService } from '../services/download-record.service';
import { ProgrammeOpsService } from '../services/programme-ops.service';

describe('ProgrammeOpsPageComponent', () => {
  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ProgrammeOpsPageComponent],
      providers: [
        {
          provide: ProgrammeOpsService,
          useValue: {
            list: () =>
              of({
                programmes: [
                  {
                    uuid: '11111111-1111-1111-1111-111111111111',
                    programme_code: 'NBMS-CORE-PROGRAMME',
                    title: 'NBMS Core Indicator Operations',
                    programme_type: 'national',
                    refresh_cadence: 'monthly',
                    scheduler_enabled: true,
                    next_run_at: null,
                    last_run_at: null,
                    lead_org: 'SANBI',
                    open_alert_count: 0,
                    latest_run_status: 'succeeded',
                    dataset_link_count: 2,
                    indicator_link_count: 2
                  }
                ]
              }),
            detail: () =>
              of({
                programme: {
                  uuid: '11111111-1111-1111-1111-111111111111',
                  programme_code: 'NBMS-CORE-PROGRAMME',
                  title: 'NBMS Core Indicator Operations',
                  programme_type: 'national',
                  refresh_cadence: 'monthly',
                  scheduler_enabled: true,
                  next_run_at: null,
                  last_run_at: null,
                  lead_org: 'SANBI',
                  open_alert_count: 0,
                  latest_run_status: 'succeeded',
                  dataset_link_count: 2,
                  indicator_link_count: 2,
                  description: 'Core pipeline',
                  geographic_scope: 'South Africa',
                  taxonomic_scope: 'Biodiversity',
                  ecosystem_scope: 'All',
                  consent_required: false,
                  sensitivity_class: 'INT',
                  agreement_code: null,
                  pipeline_definition_json: { steps: [{ key: 'ingest', type: 'ingest' }] },
                  data_quality_rules_json: { minimum_dataset_links: 1 },
                  lineage_notes: 'Lineage',
                  website_url: '',
                  operating_institutions: [{ id: 1, name: 'SANBI', org_code: 'SANBI' }],
                  partners: [],
                  stewards: [{ user_id: 1, username: 'programme_steward', role: 'owner', is_primary: true }]
                },
                runs: [],
                alerts: [],
                can_manage: true
              }),
            run: () =>
              of({
                uuid: '22222222-2222-2222-2222-222222222222',
                run_type: 'full',
                trigger: 'manual',
                status: 'succeeded',
                dry_run: false,
                requested_by: 'programme_steward',
                started_at: null,
                finished_at: null,
                input_summary_json: {},
                output_summary_json: {},
                lineage_json: {},
                log_excerpt: '',
                error_message: '',
                created_at: '2026-02-06T00:00:00Z',
                steps: []
              }),
            rerun: () =>
              of({
                uuid: '33333333-3333-3333-3333-333333333333',
                run_type: 'full',
                trigger: 'manual',
                status: 'succeeded',
                dry_run: false,
                requested_by: 'programme_steward',
                started_at: null,
                finished_at: null,
                input_summary_json: {},
                output_summary_json: {},
                lineage_json: {},
                log_excerpt: '',
                error_message: '',
                created_at: '2026-02-06T00:00:00Z',
                steps: []
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

  it('renders programme operations workspace', async () => {
    const fixture = TestBed.createComponent(ProgrammeOpsPageComponent);
    fixture.detectChanges();
    await fixture.whenStable();
    fixture.detectChanges();
    const compiled = fixture.nativeElement as HTMLElement;
    expect(compiled.textContent).toContain('Programme Registry');
    expect(compiled.textContent).toContain('NBMS Core Indicator Operations');
    expect(compiled.textContent).toContain('Run now');
  });
});
