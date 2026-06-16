import { Injectable, signal } from '@angular/core';

@Injectable({
  providedIn: 'root',
})
export class LeftSidebarService {
  isOpen = signal<boolean>(false);

  open(): void {
    this.isOpen.set(true);
    document.body.style.overflow = 'hidden';
  }

  close(): void {
    this.isOpen.set(false);
    document.body.style.overflow = '';
  }
}