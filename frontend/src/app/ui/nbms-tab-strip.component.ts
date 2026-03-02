import { ChangeDetectionStrategy, Component, EventEmitter, Input, Output } from '@angular/core';
import { NgFor, NgIf } from '@angular/common';

type NbmsTabItem = {
  id: string;
  label: string;
  count?: number | null;
  disabled?: boolean;
};

@Component({
  selector: 'nbms-tab-strip',
  standalone: true,
  imports: [NgFor, NgIf],
  template: `
    <nav class="tab-strip nbms-card-surface" role="tablist">
      <button
        *ngFor="let tab of tabs; trackBy: trackByTab"
        type="button"
        class="tab"
        role="tab"
        [disabled]="tab.disabled"
        [class.tab--active]="tab.id === activeTab"
        [attr.aria-selected]="tab.id === activeTab"
        [attr.tabindex]="tab.id === activeTab ? 0 : -1"
        (click)="tabChange.emit(tab.id)"
      >
        <span>{{ tab.label }}</span>
        <strong *ngIf="tab.count !== undefined && tab.count !== null">{{ tab.count }}</strong>
      </button>
    </nav>
  `,
  styles: [
    `
      .tab-strip {
        display: inline-flex;
        gap: var(--nbms-space-2);
        padding: var(--nbms-space-2);
      }

      .tab {
        display: inline-flex;
        align-items: center;
        gap: var(--nbms-space-2);
        border: 1px solid transparent;
        border-radius: var(--nbms-radius-pill);
        background: transparent;
        color: var(--nbms-text-secondary);
        cursor: pointer;
        font: inherit;
        font-weight: 700;
        padding: var(--nbms-space-2) var(--nbms-space-3);
      }

      .tab strong {
        border-radius: var(--nbms-radius-pill);
        background: var(--nbms-surface-muted);
        color: var(--nbms-text-primary);
        font-size: var(--nbms-font-size-label-sm);
        padding: 0 var(--nbms-space-2);
      }

      .tab--active {
        background: color-mix(in srgb, var(--nbms-color-primary-500) 10%, transparent);
        border-color: color-mix(in srgb, var(--nbms-color-primary-500) 26%, var(--nbms-surface));
        color: var(--nbms-color-primary-700);
      }

      .tab:focus-visible {
        outline: none;
        box-shadow: var(--nbms-focus-ring);
      }
    `
  ],
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class NbmsTabStripComponent {
  @Input() tabs: NbmsTabItem[] = [];
  @Input() activeTab = '';

  @Output() tabChange = new EventEmitter<string>();

  trackByTab(_: number, tab: NbmsTabItem): string {
    return tab.id;
  }
}
