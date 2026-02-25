import { ChangeDetectionStrategy, Component, EventEmitter, Input, Output } from '@angular/core';
import { NgFor, NgIf } from '@angular/common';
import { FormControl, ReactiveFormsModule } from '@angular/forms';
import { MatIconModule } from '@angular/material/icon';
import { debounceTime, map, startWith } from 'rxjs';

export type NbmsCommand = {
  id: string;
  label: string;
  route?: string;
  icon?: string;
};

@Component({
  selector: 'nbms-command-palette',
  standalone: true,
  imports: [NgFor, NgIf, ReactiveFormsModule, MatIconModule],
  template: `
    <div class="palette-backdrop" (click)="closed.emit()"></div>
    <section class="palette nbms-card-surface" role="dialog" aria-label="Command palette">
      <header>
        <mat-icon>search</mat-icon>
        <input
          type="text"
          [formControl]="query"
          placeholder="Type a command (Ctrl/Cmd+K)"
          aria-label="Command search"
        />
      </header>
      <button type="button" *ngFor="let item of filteredCommands; trackBy: trackByCommand" (click)="selected.emit(item)">
        <mat-icon *ngIf="item.icon">{{ item.icon }}</mat-icon>
        <span>{{ item.label }}</span>
      </button>
      <p *ngIf="!filteredCommands.length">No matching commands.</p>
    </section>
  `,
  styles: [
    `
      :host {
        position: fixed;
        inset: 0;
        z-index: 2000;
      }

      .palette-backdrop {
        position: absolute;
        inset: 0;
        background: rgb(15 23 32 / 42%);
      }

      .palette {
        position: absolute;
        top: min(10vh, 4rem);
        left: 50%;
        transform: translateX(-50%);
        width: min(38rem, calc(100vw - 2rem));
        display: grid;
        gap: var(--nbms-space-1);
        padding: var(--nbms-space-2);
      }

      header {
        display: grid;
        grid-template-columns: 1.3rem 1fr;
        align-items: center;
        gap: var(--nbms-space-2);
        border: 1px solid var(--nbms-border);
        border-radius: var(--nbms-radius-sm);
        padding: 0.2rem 0.6rem;
      }

      header mat-icon {
        color: var(--nbms-text-muted);
      }

      header input {
        border: 0;
        outline: none;
        background: transparent;
        color: var(--nbms-text-primary);
        font-size: var(--nbms-font-size-base);
        padding: 0.35rem 0;
      }

      button {
        border: 0;
        text-align: left;
        display: grid;
        grid-template-columns: 1.3rem 1fr;
        align-items: center;
        gap: var(--nbms-space-2);
        padding: 0.55rem 0.45rem;
        border-radius: var(--nbms-radius-sm);
        background: transparent;
        color: var(--nbms-text-primary);
        cursor: pointer;
      }

      button:hover {
        background: var(--nbms-surface-muted);
      }

      p {
        margin: 0;
        padding: 0.4rem 0.6rem;
        color: var(--nbms-text-muted);
        font-size: var(--nbms-font-size-label);
      }
    `
  ],
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class NbmsCommandPaletteComponent {
  @Input() commands: NbmsCommand[] = [];
  @Output() closed = new EventEmitter<void>();
  @Output() selected = new EventEmitter<NbmsCommand>();

  readonly query = new FormControl('', { nonNullable: true });
  filteredCommands: NbmsCommand[] = [];

  constructor() {
    this.query.valueChanges
      .pipe(
        startWith(''),
        debounceTime(100),
        map((value) => value.trim().toLowerCase())
      )
      .subscribe((query) => {
        this.filteredCommands = this.commands.filter((item) =>
          item.label.toLowerCase().includes(query)
        );
      });
  }

  ngOnChanges(): void {
    const current = (this.query.value || '').trim().toLowerCase();
    this.filteredCommands = this.commands.filter((item) =>
      item.label.toLowerCase().includes(current)
    );
  }

  trackByCommand(_: number, command: NbmsCommand): string {
    return command.id;
  }
}
