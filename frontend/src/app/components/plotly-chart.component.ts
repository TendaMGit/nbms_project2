import { CommonModule } from '@angular/common';
import {
  AfterViewInit,
  ChangeDetectionStrategy,
  Component,
  ElementRef,
  Input,
  OnChanges,
  SimpleChanges,
  ViewChild
} from '@angular/core';

type PlotlySpec = {
  data: Array<Record<string, unknown>>;
  layout: Record<string, unknown>;
  config: Record<string, unknown>;
};

@Component({
  selector: 'app-plotly-chart',
  standalone: true,
  imports: [CommonModule],
  template: `<div #host class="plot-host"></div>`,
  styles: [
    `
      .plot-host {
        width: 100%;
        min-height: 260px;
      }
    `
  ],
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class PlotlyChartComponent implements AfterViewInit, OnChanges {
  @Input() spec: PlotlySpec | null = null;
  @ViewChild('host', { static: true }) private readonly hostRef!: ElementRef<HTMLDivElement>;

  private initialized = false;

  async ngAfterViewInit(): Promise<void> {
    this.initialized = true;
    await this.render();
  }

  async ngOnChanges(_changes: SimpleChanges): Promise<void> {
    if (!this.initialized) {
      return;
    }
    await this.render();
  }

  private async render(): Promise<void> {
    if (!this.spec) {
      this.hostRef.nativeElement.innerHTML = '';
      return;
    }
    const plotlyModule = await import('plotly.js-dist-min');
    const Plotly = (plotlyModule as unknown as { default?: unknown }).default || (plotlyModule as unknown);
    const data = this.spec.data || [];
    const layout = this.spec.layout || {};
    const config = { responsive: true, ...(this.spec.config || {}) };
    await (Plotly as { react: (...args: unknown[]) => Promise<void> }).react(
      this.hostRef.nativeElement,
      data,
      layout,
      config
    );
  }
}
