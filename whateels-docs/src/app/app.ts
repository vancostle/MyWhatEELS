import { Component, inject, PLATFORM_ID, signal } from '@angular/core';
import { isPlatformBrowser } from '@angular/common';
import { Router, RouterOutlet, NavigationEnd } from '@angular/router';
import { filter } from 'rxjs';

@Component({
  selector: 'app-root',
  imports: [RouterOutlet],
  templateUrl: './app.html',
  styleUrl: './app.css'
})
export class App {
  protected readonly title = signal('whateels-docs');

  constructor() {
    const platformId = inject(PLATFORM_ID);
    if (isPlatformBrowser(platformId)) {
      const router = inject(Router);
      router.events.pipe(filter(e => e instanceof NavigationEnd)).subscribe(() => {
        const fragment = router.parseUrl(router.url).fragment;
        if (fragment) {
          setTimeout(() => document.getElementById(fragment)?.scrollIntoView({ behavior: 'smooth', block: 'start' }), 0);
        }
      });
    }
  }
}
