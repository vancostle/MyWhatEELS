import { Injectable, signal } from '@angular/core';

export type EmailStatusState = 'loading' | 'success' | 'error';

@Injectable({
  providedIn: 'root',
})
export class EmailStatusService {
  isOpen = signal<boolean>(false);
  state = signal<EmailStatusState>('loading');

  open(state: EmailStatusState = 'loading'): void {
    this.state.set(state);
    this.isOpen.set(true);
  }

  close(): void {
    this.isOpen.set(false);
  }

  showLoading(): void {
    this.open('loading');
  }

  showSuccess(): void {
    this.open('success');
  }

  showError(): void {
    this.open('error');
  }
}