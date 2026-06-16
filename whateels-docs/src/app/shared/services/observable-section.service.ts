import { Injectable, signal, inject, PLATFORM_ID } from '@angular/core';
import { isPlatformBrowser } from '@angular/common';

@Injectable({
  providedIn: 'root',
})
export class ObservableSectionService {
  private platformId = inject(PLATFORM_ID);
  activeSectionId = signal<string | null>(null);
  private observer: IntersectionObserver | null = null;
  private isInitialized = false;
  private observedElements = new Set<HTMLElement>();

  private initializeObserver(): void {
    if (!isPlatformBrowser(this.platformId) || this.isInitialized) {
      return;
    }

    const root = document.documentElement;
    const style = getComputedStyle(root);
    const toPx = (value: string): number => {
      const v = value.trim();
      if (v.endsWith('rem')) return parseFloat(v) * 16;
      return parseFloat(v);
    };

    const headerHeightPx = toPx(style.getPropertyValue('--header-height'));
    const contentMarginPx = toPx(style.getPropertyValue('--margin-header-content'));
    const topOffsetPx = headerHeightPx + contentMarginPx;
    const topMargin = -topOffsetPx;

    // Keep only a very small detection band at the exact top offset line.
    const viewportHeightPx = window.innerHeight || document.documentElement.clientHeight;
    const bandHeightPx = 1;
    const bottomMargin = -Math.max(1, viewportHeightPx - topOffsetPx - bandHeightPx);

    const options = {
      root: null,
      rootMargin: `${topMargin}px 0px ${bottomMargin}px 0px`,
      threshold: 0,
    };

    this.observer = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          this.activeSectionId.set(entry.target.id);
        }
      });
    }, options);

    this.isInitialized = true;
  }

  registerElement(element: HTMLElement): void {
    this.initializeObserver();
    this.observer?.observe(element);
  }

  unregisterElement(element: HTMLElement): void {
    this.observer?.unobserve(element);
    this.observedElements.delete(element);
  }

  observeElements(elements: HTMLElement[]): void {
    this.initializeObserver();

    this.observedElements.forEach((element) => {
      this.observer?.unobserve(element);
    });
    this.observedElements.clear();

    elements.forEach((element) => {
      if (!element.id) {
        return;
      }

      this.observer?.observe(element);
      this.observedElements.add(element);
    });
  }
}
