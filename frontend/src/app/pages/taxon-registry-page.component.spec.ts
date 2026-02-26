import { TestBed } from '@angular/core/testing';
import { of } from 'rxjs';

import { RegistryService } from '../services/registry.service';
import { TaxonRegistryPageComponent } from './taxon-registry-page.component';

describe('TaxonRegistryPageComponent', () => {
  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [TaxonRegistryPageComponent],
      providers: [
        {
          provide: RegistryService,
          useValue: {
            listTaxa: () =>
              of({
                count: 1,
                page: 1,
                page_size: 25,
                results: [
                  {
                    uuid: 'tax-1',
                    taxon_code: 'ZA-TAX-0001',
                    scientific_name: 'Panthera leo',
                    canonical_name: 'Panthera leo',
                    taxon_rank: 'species',
                    taxonomic_status: 'accepted',
                    kingdom: 'Animalia',
                    family: 'Felidae',
                    genus: 'Panthera',
                    is_native: true,
                    is_endemic: false,
                    has_national_voucher_specimen: true,
                    voucher_specimen_count: 2,
                    primary_source_system: 'gbif_species_match',
                    status: 'published',
                    sensitivity: 'public',
                    qa_status: 'published',
                    organisation: 'SANBI',
                    updated_at: '2026-02-08T00:00:00Z'
                  }
                ]
              }),
            taxonDetail: () =>
              of({
                taxon: {
                  uuid: 'tax-1',
                  taxon_code: 'ZA-TAX-0001',
                  scientific_name: 'Panthera leo',
                  canonical_name: 'Panthera leo',
                  taxon_rank: 'species',
                  taxonomic_status: 'accepted',
                  kingdom: 'Animalia',
                  family: 'Felidae',
                  genus: 'Panthera',
                  is_native: true,
                  is_endemic: false,
                  has_national_voucher_specimen: true,
                  voucher_specimen_count: 2,
                  primary_source_system: 'gbif_species_match',
                  status: 'published',
                  sensitivity: 'public',
                  qa_status: 'published',
                  organisation: 'SANBI',
                  updated_at: '2026-02-08T00:00:00Z',
                  classification: {
                    kingdom: 'Animalia',
                    phylum: 'Chordata',
                    class_name: 'Mammalia',
                    order: 'Carnivora',
                    family: 'Felidae',
                    genus: 'Panthera',
                    species: 'leo'
                  },
                  gbif_taxon_key: 1,
                  gbif_usage_key: 1,
                  gbif_accepted_taxon_key: 1
                },
                names: [],
                source_records: [],
                vouchers: []
              })
          }
        }
      ]
    }).compileComponents();
  });

  it('renders taxon registry list', async () => {
    const fixture = TestBed.createComponent(TaxonRegistryPageComponent);
    fixture.detectChanges();
    await fixture.whenStable();
    fixture.detectChanges();
    const compiled = fixture.nativeElement as HTMLElement;
    expect(compiled.textContent).toContain('Taxon Registry');
    expect(compiled.textContent).toContain('ZA-TAX-0001');
  });
});
