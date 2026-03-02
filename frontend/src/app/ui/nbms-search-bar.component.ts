import { ChangeDetectionStrategy, Component, EventEmitter, Input, Output } from '@angular/core';
import { FormControl, ReactiveFormsModule } from '@angular/forms';
import { NgFor, NgIf } from '@angular/common';
import { debounceTime, distinctUntilChanged } from 'rxjs';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';

export type NbmsSearchResult = {
  id: string;
  title: string;
  subtitle: string;
  kind: 'framework' | 'target' | 'indicator';
  route: string | any[];
};

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
          (keydown.enter)="submitQuery()"
        />
        <mat-icon matPrefix>search</mat-icon>
      </mat-form-field>

      <div class="results nbms-card-surface" *ngIf="showResults && query.value.trim().length && results.length">
        <button
          type="button"
          class="result"
          *ngFor="let item of results; trackBy: trackResult"
          (click)="pickResult(item)"
        >
          <span class="result-kind">{{ item.kind }}</span>
          <strong>{{ item.title }}</strong>
          <small>{{ item.subtitle }}</small>
        </button>
      </div>

      <div class="recent" *ngIf="showRecent && !query.value.trim().length && recent.length">
        <button type="button" *ngFor="let item of recent; trackBy: trackByValue" (click)="pickRecent(item)">
          {{ item }}
        </button>
      </div>
    </div>
  `,
  styles: [
    `
      .search-bar {
        position: relative;
        min-width: 16rem;
      }

      mat-form-field {
        width: 100%;
      }

      .results {
        position: absolute;
        top: calc(100% + var(--nbms-space-1));
        left: 0;
        right: 0;
        z-index: 12;
        display: grid;
        gap: 1px;
        padding: var(--nbms-space-1);
        background: var(--nbms-surface);
      }

      .result {
        display: grid;
        gap: 0.1rem;
        border: 0;
        border-radius: var(--nbms-radius-sm);
        background: transparent;
        color: var(--nbms-text-primary);
        cursor: pointer;
        padding: var(--nbms-space-2) var(--nbms-space-3);
        text-align: left;
      }

      .result:hover,
      .result:focus-visible {
        background: color-mix(in srgb, var(--nbms-accent-100) 72%, var(--nbms-surface));
        outline: none;
      }

      .result-kind,
      .result small {
        color: var(--nbms-text-muted);
      }

      .result-kind {
        font-size: var(--nbms-font-size-label-sm);
        font-weight: 700;
        letter-spacing: 0.06em;
        text-transform: uppercase;
      }

      .result strong,
      .result small {
        margin: 0;
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
  @Input() placeholder = 'Search frameworks, targets, indicators';
  @Input() showRecent = true;
  @Input() showResults = true;
  @Input() results: NbmsSearchResult[] = [];
  @Output() queryChange = new EventEmitter<string>();
  @Output() submitted = new EventEmitter<string>();
  @Output() resultSelected = new EventEmitter<NbmsSearchResult>();

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

  pickResult(result: NbmsSearchResult): void {
    this.resultSelected.emit(result);
  }

  submitQuery(): void {
    const value = (this.query.value || '').trim();
    if (!value) {
      return;
    }
    this.saveRecent(value);
    this.submitted.emit(value);
  }

  trackResult(_: number, result: NbmsSearchResult): string {
    return result.id;
  }

  private saveRecent(value: string): void {
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
