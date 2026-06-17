import { Injectable, signal } from '@angular/core';

@Injectable({
  providedIn: 'root',
})
export class SearchModalService {
  isOpen = signal<boolean>(false);

  open(): void {
    this.isOpen.set(true);
    document.body.style.overflow = 'hidden';
  }

  close(): void {
    this.isOpen.set(false);
    document.body.style.overflow = '';
  }

  toggle(): void {
    this.isOpen.set(!this.isOpen());
  }
}