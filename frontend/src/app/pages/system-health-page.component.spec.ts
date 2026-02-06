import { TestBed } from '@angular/core/testing';
import { of } from 'rxjs';

import { SystemHealthPageComponent } from './system-health-page.component';
import { SystemHealthService } from '../services/system-health.service';

describe('SystemHealthPageComponent', () => {
  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [SystemHealthPageComponent],
      providers: [
        {
          provide: SystemHealthService,
          useValue: {
            getSummary: () =>
              of({
                overall_status: 'ok',
                services: [
                  { service: 'database', status: 'ok' },
                  { service: 'storage', status: 'disabled' },
                  { service: 'cache', status: 'ok' }
                ],
                recent_failures: []
              })
          }
        }
      ]
    }).compileComponents();
  });

  it('renders the system status panel', async () => {
    const fixture = TestBed.createComponent(SystemHealthPageComponent);
    fixture.detectChanges();
    await fixture.whenStable();
    const compiled = fixture.nativeElement as HTMLElement;
    expect(compiled.textContent).toContain('System Status');
    expect(compiled.textContent).toContain('Overall');
    expect(compiled.textContent).toContain('database');
  });
});
