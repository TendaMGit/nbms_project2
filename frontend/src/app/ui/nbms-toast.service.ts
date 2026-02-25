import { Injectable } from '@angular/core';
import { MatSnackBar } from '@angular/material/snack-bar';

@Injectable({ providedIn: 'root' })
export class NbmsToastService {
  constructor(private readonly snackBar: MatSnackBar) {}

  success(message: string): void {
    this.snackBar.open(message, 'Close', { duration: 3500, panelClass: ['nbms-toast-success'] });
  }

  warn(message: string): void {
    this.snackBar.open(message, 'Close', { duration: 4200, panelClass: ['nbms-toast-warn'] });
  }

  error(message: string): void {
    this.snackBar.open(message, 'Close', { duration: 5000, panelClass: ['nbms-toast-error'] });
  }
}
