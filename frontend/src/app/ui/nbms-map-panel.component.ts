import { ChangeDetectionStrategy, Component, Input } from '@angular/core';

@Component({
  selector: 'nbms-map-panel',
  standalone: true,
  template: `
    <section class="map-panel nbms-card-surface">
      <header>
        <h3>{{ title }}</h3>
        <ng-content select="[map-actions]"></ng-content>
      </header>
      <div class="map-body">
        <ng-content></ng-content>
      </div>
    </section>
  `,
  styles: [
    `
      .map-panel {
        overflow: hidden;
      }

      header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: var(--nbms-space-3) var(--nbms-space-4);
        border-bottom: 1px solid var(--nbms-divider);
      }

      header h3 {
        margin: 0;
        font-size: var(--nbms-font-size-h4);
      }

      .map-body {
        min-height: 320px;
      }
    `
  ],
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class NbmsMapPanelComponent {
  @Input() title = 'Map';
}
