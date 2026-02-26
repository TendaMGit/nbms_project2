import { ScrollingModule } from '@angular/cdk/scrolling';
import { ChangeDetectionStrategy, Component, Input, TemplateRef } from '@angular/core';
import { NgFor, NgIf, NgTemplateOutlet } from '@angular/common';

type ColumnDef<T> = {
  key: string;
  label: string;
};

@Component({
  selector: 'nbms-data-table',
  standalone: true,
  imports: [NgFor, NgIf, NgTemplateOutlet, ScrollingModule],
  template: `
    <section class="table-wrapper nbms-card-surface">
      <header class="table-header">
        <h3>{{ title }}</h3>
        <ng-content select="[table-actions]"></ng-content>
      </header>

      <div class="header-row">
        <span *ngFor="let col of columns; trackBy: trackByColumn">{{ col.label }}</span>
      </div>

      <cdk-virtual-scroll-viewport class="viewport" [itemSize]="itemSize">
        <div class="row" *cdkVirtualFor="let item of rows; trackBy: trackByIndex">
          <span *ngFor="let col of columns; trackBy: trackByColumn">
            <ng-container *ngIf="cellTemplate; else textCell">
              <ng-container
                *ngTemplateOutlet="cellTemplate; context: { $implicit: item, key: col.key }"
              ></ng-container>
            </ng-container>
            <ng-template #textCell>{{ readCell(item, col.key) }}</ng-template>
          </span>
        </div>
      </cdk-virtual-scroll-viewport>

      <p class="table-empty" *ngIf="!rows.length">No rows to display.</p>
    </section>
  `,
  styles: [
    `
      .table-wrapper {
        overflow: hidden;
      }

      .table-header {
        padding: var(--nbms-space-4);
        border-bottom: 1px solid var(--nbms-divider);
        display: flex;
        align-items: center;
        justify-content: space-between;
      }

      .table-header h3 {
        margin: 0;
        font-size: var(--nbms-font-size-h4);
      }

      .header-row,
      .row {
        display: grid;
        grid-template-columns: repeat(var(--nbms-table-columns, 1), minmax(0, 1fr));
        gap: var(--nbms-space-2);
        align-items: center;
      }

      .header-row {
        padding: var(--nbms-space-2) var(--nbms-space-4);
        background: var(--nbms-surface-muted);
        color: var(--nbms-text-secondary);
        font-size: var(--nbms-font-size-label-sm);
        font-weight: 700;
      }

      .viewport {
        height: min(66vh, 540px);
      }

      .row {
        min-height: 46px;
        padding: 0 var(--nbms-space-4);
        border-bottom: 1px solid var(--nbms-divider);
        font-size: var(--nbms-font-size-dense);
      }

      .table-empty {
        margin: 0;
        padding: var(--nbms-space-4);
        color: var(--nbms-text-muted);
      }
    `
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
  host: {
    '[style.--nbms-table-columns]': 'columns.length'
  }
})
export class NbmsDataTableComponent<T extends object> {
  @Input() title = 'Data table';
  @Input() rows: T[] = [];
  @Input() columns: Array<ColumnDef<T>> = [];
  @Input() itemSize = 46;
  @Input() cellTemplate: TemplateRef<{ $implicit: T; key: string }> | null = null;

  trackByColumn(_: number, column: ColumnDef<T>): string {
    return column.key;
  }

  trackByIndex(index: number): number {
    return index;
  }

  readCell(item: T, key: string): unknown {
    return (item as Record<string, unknown>)[key];
  }
}
