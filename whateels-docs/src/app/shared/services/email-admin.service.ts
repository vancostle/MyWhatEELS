import { Injectable, signal } from '@angular/core';

@Injectable({
  providedIn: 'root',
})
export class EmailAdminService {
  isOpen = signal<boolean>(true);

  open(): void {
    this.isOpen.set(true);
  }

  close(): void {
    this.isOpen.set(false);
  }

  toggle(): void {
    if (this.isOpen()) {
      this.close();
    } else {
      this.open();
    }
  }
}
