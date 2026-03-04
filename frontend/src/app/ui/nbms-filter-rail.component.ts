import { ChangeDetectionStrategy, Component, Input } from '@angular/core';

@Component({
  selector: 'nbms-filter-rail',
  standalone: true,
  template: `
    <aside class="filter-rail nbms-card-surface">
      <h3>{{ title }}</h3>
      <ng-content></ng-content>
    </aside>
  `,
  styles: [
    `
      .filter-rail {
        padding: var(--nbms-space-4) var(--nbms-space-5);
        display: grid;
        gap: var(--nbms-space-3);
      }

      .filter-rail h3 {
        margin: 0;
        font-size: var(--nbms-font-size-h4);
        letter-spacing: -0.01em;
      }
    `
  ],
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class NbmsFilterRailComponent {
  @Input() title = 'Filters';
}
