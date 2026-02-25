import { ChangeDetectionStrategy, Component, EventEmitter, Input, Output } from '@angular/core';
import { FormControl, ReactiveFormsModule } from '@angular/forms';
import { NgFor, NgIf } from '@angular/common';
import { debounceTime, distinctUntilChanged } from 'rxjs';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';

@Component({
  selector: 'nbms-search-bar',
  standalone: true,
  imports: [ReactiveFormsModule, NgFor, NgIf, MatFormFieldModule, MatIconModule, MatInputModule],
  template: `
    <div class="search-bar">
      <mat-form-field appearance="outline" subscriptSizing="dynamic">
        <mat-label>{{ placeholder }}</mat-label>
        <input
          matInput
          [formControl]="query"
          [attr.aria-label]="placeholder"
          (keydown.enter)="saveRecent()"
        />
        <mat-icon matPrefix>search</mat-icon>
      </mat-form-field>

      <div class="recent" *ngIf="showRecent && recent.length">
        <button type="button" *ngFor="let item of recent; trackBy: trackByValue" (click)="pickRecent(item)">
          {{ item }}
        </button>
      </div>
    </div>
  `,
  styles: [
    `
      .search-bar {
        min-width: 16rem;
      }

      mat-form-field {
        width: 100%;
      }

      .recent {
        margin-top: -0.25rem;
        display: flex;
        flex-wrap: wrap;
        gap: 0.4rem;
      }

      .recent button {
        border: 1px solid var(--nbms-border);
        border-radius: var(--nbms-radius-pill);
        background: var(--nbms-surface);
        color: var(--nbms-text-secondary);
        padding: 0.15rem 0.55rem;
        font-size: var(--nbms-font-size-label-sm);
        cursor: pointer;
      }
    `
  ],
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class NbmsSearchBarComponent {
  @Input() placeholder = 'Search indicators, targets, datasets';
  @Input() showRecent = true;
  @Output() queryChange = new EventEmitter<string>();

  readonly query = new FormControl('', { nonNullable: true });
  recent: string[] = [];

  private readonly storageKey = 'nbms.search.recent';

  constructor() {
    this.recent = this.readRecent();
    this.query.valueChanges.pipe(debounceTime(220), distinctUntilChanged()).subscribe((value) => {
      this.queryChange.emit((value || '').trim());
    });
  }

  pickRecent(value: string): void {
    this.query.setValue(value);
    this.queryChange.emit(value);
  }

  saveRecent(): void {
    const value = (this.query.value || '').trim();
    if (!value) {
      return;
    }
    this.recent = [value, ...this.recent.filter((entry) => entry !== value)].slice(0, 8);
    localStorage.setItem(this.storageKey, JSON.stringify(this.recent));
  }

  trackByValue(_: number, value: string): string {
    return value;
  }

  private readRecent(): string[] {
    const raw = localStorage.getItem(this.storageKey);
    if (!raw) {
      return [];
    }
    try {
      const parsed = JSON.parse(raw);
      if (!Array.isArray(parsed)) {
        return [];
      }
      return parsed.filter((entry) => typeof entry === 'string');
    } catch {
      return [];
    }
  }
}
