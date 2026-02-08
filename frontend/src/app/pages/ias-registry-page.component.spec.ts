import { TestBed } from '@angular/core/testing';
import { of } from 'rxjs';

import { IasRegistryPageComponent } from './ias-registry-page.component';
import { RegistryService } from '../services/registry.service';

describe('IasRegistryPageComponent', () => {
  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [IasRegistryPageComponent],
      providers: [
        {
          provide: RegistryService,
          useValue: {
            listIas: () =>
              of({
                count: 1,
                page: 1,
                page_size: 25,
                results: [
                  {
                    uuid: 'ias-1',
                    taxon_uuid: 'tax-1',
                    taxon_code: 'IAS-TAX-001',
                    scientific_name: 'Acacia mearnsii',
                    country_code: 'ZA',
                    establishment_means_code: 'introduced',
                    degree_of_establishment_code: 'invasive',
                    pathway_code: 'escape',
                    is_invasive: true,
                    regulatory_status: 'unknown',
                    latest_eicat: 'MR',
                    latest_seicat: 'MN',
                    status: 'published',
                    sensitivity: 'public',
                    qa_status: 'published',
                    updated_at: '2026-02-08T00:00:00Z'
                  }
                ]
              }),
            iasDetail: () =>
              of({
                profile: {
                  uuid: 'ias-1',
                  taxon_uuid: 'tax-1',
                  taxon_code: 'IAS-TAX-001',
                  scientific_name: 'Acacia mearnsii',
                  country_code: 'ZA',
                  establishment_means_code: 'introduced',
                  degree_of_establishment_code: 'invasive',
                  pathway_code: 'escape',
                  is_invasive: true,
                  regulatory_status: 'unknown',
                  latest_eicat: 'MR',
                  latest_seicat: 'MN',
                  status: 'published',
                  sensitivity: 'public',
                  qa_status: 'published',
                  updated_at: '2026-02-08T00:00:00Z',
                  establishment_means_label: 'introduced',
                  degree_of_establishment_label: 'invasive',
                  pathway_label: 'escape',
                  habitat_types_json: []
                },
                checklist_records: [],
                eicat_assessments: [],
                seicat_assessments: []
              })
          }
        }
      ]
    }).compileComponents();
  });

  it('renders IAS registry list', async () => {
    const fixture = TestBed.createComponent(IasRegistryPageComponent);
    fixture.detectChanges();
    await fixture.whenStable();
    fixture.detectChanges();
    const compiled = fixture.nativeElement as HTMLElement;
    expect(compiled.textContent).toContain('IAS Registry');
    expect(compiled.textContent).toContain('IAS-TAX-001');
  });
});
