import { ChangeDetectionStrategy, Component } from '@angular/core';

@Component({
  selector: 'nbms-stat-strip',
  standalone: true,
  template: `
    <section class="stat-strip">
      <ng-content></ng-content>
    </section>
  `,
  styles: [
    `
      .stat-strip {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
        gap: var(--nbms-space-3);
      }
    `
  ],
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class NbmsStatStripComponent {}
