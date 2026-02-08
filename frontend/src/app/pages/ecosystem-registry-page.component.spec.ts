import { TestBed } from '@angular/core/testing';
import { of } from 'rxjs';

import { EcosystemRegistryPageComponent } from './ecosystem-registry-page.component';
import { RegistryService } from '../services/registry.service';

describe('EcosystemRegistryPageComponent', () => {
  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [EcosystemRegistryPageComponent],
      providers: [
        {
          provide: RegistryService,
          useValue: {
            listEcosystems: () =>
              of({
                count: 1,
                page: 1,
                page_size: 25,
                results: [
                  {
                    uuid: 'eco-1',
                    ecosystem_code: 'ECO-001',
                    name: 'Savanna',
                    realm: 'terrestrial',
                    biome: 'Savanna',
                    bioregion: 'South Africa',
                    vegmap_version: 'v1',
                    get_node: 'L1-Terrestrial',
                    status: 'published',
                    sensitivity: 'public',
                    qa_status: 'published',
                    organisation: 'SANBI',
                    updated_at: '2026-02-08T00:00:00Z'
                  }
                ]
              }),
            ecosystemDetail: () =>
              of({
                ecosystem: {
                  uuid: 'eco-1',
                  ecosystem_code: 'ECO-001',
                  name: 'Savanna',
                  realm: 'terrestrial',
                  biome: 'Savanna',
                  bioregion: 'South Africa',
                  vegmap_version: 'v1',
                  vegmap_source_id: 'SRC-1',
                  description: 'desc',
                  get_node: 'L1-Terrestrial',
                  status: 'published',
                  sensitivity: 'public',
                  qa_status: 'published',
                  organisation: 'SANBI',
                  updated_at: '2026-02-08T00:00:00Z'
                },
                crosswalks: [],
                risk_assessments: []
              })
          }
        }
      ]
    }).compileComponents();
  });

  it('renders ecosystem registry list', async () => {
    const fixture = TestBed.createComponent(EcosystemRegistryPageComponent);
    fixture.detectChanges();
    await fixture.whenStable();
    fixture.detectChanges();
    const compiled = fixture.nativeElement as HTMLElement;
    expect(compiled.textContent).toContain('Ecosystem Registry');
    expect(compiled.textContent).toContain('ECO-001');
  });
});
