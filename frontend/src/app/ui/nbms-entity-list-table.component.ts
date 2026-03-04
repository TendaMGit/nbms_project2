import { ChangeDetectionStrategy, Component, Input, TemplateRef } from '@angular/core';

import { NbmsDataTableComponent } from './nbms-data-table.component';

@Component({
  selector: 'nbms-entity-list-table',
  standalone: true,
  imports: [NbmsDataTableComponent],
  template: `
    <nbms-data-table
      [title]="title"
      [rows]="rows"
      [columns]="columns"
      [itemSize]="itemSize"
      [cellTemplate]="cellTemplate"
    ></nbms-data-table>
  `,
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class NbmsEntityListTableComponent<T extends object> {
  @Input() title = 'Entities';
  @Input() rows: T[] = [];
  @Input() columns: Array<{ key: string; label: string }> = [];
  @Input() itemSize = 46;
  @Input() cellTemplate: TemplateRef<{ $implicit: T; key: string }> | null = null;
}
