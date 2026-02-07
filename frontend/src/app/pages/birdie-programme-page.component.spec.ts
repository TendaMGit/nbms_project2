import { TestBed } from '@angular/core/testing';
import { of } from 'rxjs';

import { BirdieProgrammePageComponent } from './birdie-programme-page.component';
import { BirdieService } from '../services/birdie.service';

describe('BirdieProgrammePageComponent', () => {
  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [BirdieProgrammePageComponent],
      providers: [
        {
          provide: BirdieService,
          useValue: {
            dashboard: () =>
              of({
                programme: {
                  uuid: 'p1',
                  programme_code: 'NBMS-BIRDIE-INTEGRATION',
                  title: 'BIRDIE Programme',
                  programme_type: 'national',
                  refresh_cadence: 'weekly',
                  scheduler_enabled: true,
                  next_run_at: null,
                  last_run_at: null,
                  lead_org: 'SANBI',
                  open_alert_count: 0,
                  latest_run_status: 'succeeded',
                  dataset_link_count: 0,
                  indicator_link_count: 4
                },
                site_reports: [
                  {
                    site_code: 'SITE-1',
                    site_name: 'Site 1',
                    province_code: 'WC',
                    last_year: 2023,
                    abundance_index: 0.5,
                    richness: 12,
                    trend: 'up'
                  }
                ],
                species_reports: [
                  {
                    species_code: 'ANAHER',
                    common_name: 'Grey Heron',
                    guild: 'wader',
                    last_year: 2023,
                    last_value: 0.5,
                    trend: 'up'
                  }
                ],
                map_layers: [{ slug: 'birdie-occupancy-sites', name: 'Birdie Occupancy', indicator_code: 'BIRDIE' }],
                provenance: [
                  {
                    dataset_key: 'species',
                    captured_at: '2026-02-07T00:00:00Z',
                    payload_hash: 'abc',
                    source_endpoint: 'species'
                  }
                ]
              })
          }
        }
      ]
    }).compileComponents();
  });

  it('renders birdie dashboard tables', async () => {
    const fixture = TestBed.createComponent(BirdieProgrammePageComponent);
    fixture.detectChanges();
    await fixture.whenStable();
    fixture.detectChanges();
    const compiled = fixture.nativeElement as HTMLElement;
    expect(compiled.textContent).toContain('BIRDIE Programme Dashboard');
    expect(compiled.textContent).toContain('Site 1');
    expect(compiled.textContent).toContain('Grey Heron');
  });
});
