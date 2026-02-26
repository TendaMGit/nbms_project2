import { Component, Input } from '@angular/core';
import { MatIconModule } from '@angular/material/icon';
import { MatTooltipModule } from '@angular/material/tooltip';

@Component({
  selector: 'app-help-tooltip',
  standalone: true,
  imports: [MatIconModule, MatTooltipModule],
  template: `
    <button
      mat-icon-button
      type="button"
      class="help-button"
      [matTooltip]="text"
      matTooltipPosition="above"
      aria-label="Help"
    >
      <mat-icon>help_outline</mat-icon>
    </button>
  `,
  styles: [
    `
      .help-button {
        width: 28px;
        height: 28px;
        color: var(--nbms-accent);
      }
    `
  ]
})
export class HelpTooltipComponent {
  @Input() text = '';
}
