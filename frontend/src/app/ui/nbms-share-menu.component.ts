import { ChangeDetectionStrategy, Component, Input, inject } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatMenuModule } from '@angular/material/menu';
import { MatTooltipModule } from '@angular/material/tooltip';

import { NbmsToastService } from './nbms-toast.service';

@Component({
  selector: 'nbms-share-menu',
  standalone: true,
  imports: [MatButtonModule, MatIconModule, MatMenuModule, MatTooltipModule],
  template: `
    <button
      mat-stroked-button
      type="button"
      aria-label="Open share options"
      [matMenuTriggerFor]="shareMenu"
    >
      <mat-icon aria-hidden="true">share</mat-icon>
      Share
    </button>

    <mat-menu #shareMenu="matMenu">
      <button mat-menu-item type="button" aria-label="Copy deep link" (click)="copyLink()">
        <mat-icon aria-hidden="true">link</mat-icon>
        <span>Copy link</span>
      </button>
      <button mat-menu-item type="button" aria-label="Copy citation text" (click)="copyCitation()">
        <mat-icon aria-hidden="true">content_copy</mat-icon>
        <span>Copy citation</span>
      </button>
      <button
        mat-menu-item
        type="button"
        aria-label="Copy share to email text"
        (click)="copyEmailText()"
      >
        <mat-icon aria-hidden="true">mail</mat-icon>
        <span>Copy for email</span>
      </button>
      <button
        mat-menu-item
        type="button"
        aria-label="Export snapshot"
        [disabled]="snapshotPending"
        [matTooltip]="snapshotPending ? snapshotTooltip : ''"
        (click)="exportSnapshot()"
      >
        <mat-icon aria-hidden="true">photo_camera</mat-icon>
        <span>Export snapshot</span>
      </button>
    </mat-menu>
  `,
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class NbmsShareMenuComponent {
  private readonly toast = inject(NbmsToastService);

  @Input() title = 'NBMS page';
  @Input() snapshotPending = true;
  @Input() snapshotTooltip = 'Backend pending';

  async copyLink(): Promise<void> {
    const url = this.pageUrl();
    if (!url) {
      this.toast.warn('No page URL is available.');
      return;
    }
    await this.writeToClipboard(url, 'Deep link copied.', 'Could not copy the deep link.');
  }

  async copyCitation(): Promise<void> {
    const url = this.pageUrl();
    if (!url) {
      this.toast.warn('No page URL is available.');
      return;
    }
    const dateLabel = new Intl.DateTimeFormat('en-ZA', {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    }).format(new Date());
    await this.writeToClipboard(`${this.title}. Accessed ${dateLabel}. ${url}`, 'Citation copied.', 'Could not copy the citation.');
  }

  async copyEmailText(): Promise<void> {
    const url = this.pageUrl();
    if (!url) {
      this.toast.warn('No page URL is available.');
      return;
    }
    const body = `${this.title}\n${url}`;
    await this.writeToClipboard(body, 'Email-ready text copied.', 'Could not copy the share text.');
  }

  exportSnapshot(): void {
    this.toast.warn(this.snapshotTooltip);
  }

  private pageUrl(): string {
    return globalThis.location?.href || '';
  }

  private async writeToClipboard(value: string, successMessage: string, errorMessage: string): Promise<void> {
    if (!globalThis.navigator?.clipboard) {
      this.toast.warn('Clipboard access is not available.');
      return;
    }
    try {
      await globalThis.navigator.clipboard.writeText(value);
      this.toast.success(successMessage);
    } catch {
      this.toast.error(errorMessage);
    }
  }
}
