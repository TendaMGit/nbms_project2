import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { of } from 'rxjs';

import { ProgrammeTemplatesPageComponent } from './programme-templates-page.component';
import { RegistryService } from '../services/registry.service';

describe('ProgrammeTemplatesPageComponent', () => {
  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ProgrammeTemplatesPageComponent],
      providers: [
        provideRouter([]),
        {
          provide: RegistryService,
          useValue: {
            programmeTemplates: () =>
              of({
                templates: [
                  {
                    uuid: 'tmpl-1',
                    template_code: 'NBMS-PROG-ECOSYSTEMS',
                    title: 'NBMS Ecosystems Programme',
                    description: 'desc',
                    domain: 'ecosystems',
                    pipeline_definition_json: { steps: [{ key: 'ingest', type: 'ingest' }] },
                    required_outputs_json: [{ code: 'ecosystem_registry', label: 'Ecosystem registry table' }],
                    status: 'published',
                    sensitivity: 'public',
                    qa_status: 'published',
                    organisation: 'SANBI',
                    updated_at: '2026-02-08T00:00:00Z',
                    linked_programme_uuid: 'prog-1'
                  }
                ]
              })
          }
        }
      ]
    }).compileComponents();
  });

  it('renders programme template rows', async () => {
    const fixture = TestBed.createComponent(ProgrammeTemplatesPageComponent);
    fixture.detectChanges();
    await fixture.whenStable();
    fixture.detectChanges();
    const compiled = fixture.nativeElement as HTMLElement;
    expect(compiled.textContent).toContain('Programme Templates');
    expect(compiled.textContent).toContain('NBMS-PROG-ECOSYSTEMS');
  });
});
