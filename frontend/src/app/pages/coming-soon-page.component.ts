import { ChangeDetectionStrategy, Component, inject } from '@angular/core';
import { NgIf } from '@angular/common';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';

@Component({
  selector: 'app-coming-soon-page',
  standalone: true,
  imports: [NgIf, RouterLink, MatButtonModule],
  template: `
    <section class="coming nbms-card-surface">
      <h1>{{ title }}</h1>
      <p>{{ description }}</p>
      <div class="actions" *ngIf="fallbackRoute">
        <a mat-flat-button color="primary" [routerLink]="fallbackRoute">Open available workspace</a>
      </div>
    </section>
  `,
  styles: [
    `
      .coming {
        padding: var(--nbms-space-8);
        display: grid;
        gap: var(--nbms-space-3);
      }

      .coming h1 {
        margin: 0;
        font-size: var(--nbms-font-size-h2);
      }

      .coming p {
        margin: 0;
        color: var(--nbms-text-secondary);
      }
    `
  ],
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class ComingSoonPageComponent {
  private readonly route = inject(ActivatedRoute);

  readonly title = (this.route.snapshot.data['title'] as string) || 'Coming soon';
  readonly description =
    (this.route.snapshot.data['description'] as string) ||
    'This screen is being modernized as part of the One Biodiversity UI rollout.';
  readonly fallbackRoute = (this.route.snapshot.data['fallbackRoute'] as string) || '';
}
