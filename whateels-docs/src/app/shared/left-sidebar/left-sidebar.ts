import { isPlatformBrowser } from '@angular/common';
import { Component, ElementRef, HostBinding, inject, PLATFORM_ID, ViewChild } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { HttpClient } from '@angular/common/http';
import { ActivatedRoute } from '@angular/router';
import { catchError, combineLatest, map, of, timeout } from 'rxjs';
import { Section } from './section/section';
import { Logo } from '../logo/logo';
import { LeftSidebarService } from '../services/leftsidebar.service';

type PagesIndexResponse = { categories: { name: string; pages: string[] }[] };

@Component({
  selector: 'app-left-sidebar',
  standalone: true,
  imports: [Section, Logo],
  templateUrl: './left-sidebar.html',
  styleUrl: './left-sidebar.css',
})
export class LeftSidebar {
  private readonly platformId = inject(PLATFORM_ID);
  private readonly http = inject(HttpClient);
  private readonly route = inject(ActivatedRoute);
  private readonly scrollStorageKey = 'left-sidebar-scroll-top';
  @ViewChild('sidebarScrollContainer') private readonly sidebarScrollContainer?: ElementRef<HTMLElement>;

  private readonly pagesIndex$ = this.http.get<PagesIndexResponse>('assets/pages-index.json').pipe(
    timeout(5000),
    catchError(() => of({ categories: [] }))
  );

  readonly sections = toSignal(
    combineLatest([
      this.pagesIndex$,
      this.route.paramMap.pipe(map((params) => params.get('page'))),
    ]).pipe(
      map(([response, currentPage]) =>
        response.categories.map((category) => ({
          title: category.name,
          href: `/${this.slugify(category.name)}/index`,
          items: category.pages
            .filter((page) => page !== 'index')
            .map((page) => ({
              name: page,
              href: `/${this.slugify(category.name)}/${this.slugify(page)}`,
              isActive: this.slugify(page) === currentPage,
            })),
        }))
      )
    ),
    { initialValue: [] }
  );

  constructor(public leftSidebarService: LeftSidebarService) {}

  onNavigationClick(event: MouseEvent): void {
    const target = event.target;

    if (target instanceof Element && target.closest('a')) {
      this.leftSidebarService.close();
    }
  }

  @HostBinding('class.active')
  get isActive(): boolean {
    return this.leftSidebarService.isOpen();
  }

  ngAfterViewInit(): void {
    this.restoreScrollPosition();
  }

  private restoreScrollPosition(): void {
    if (!isPlatformBrowser(this.platformId)) {
      return;
    }

    const container = this.sidebarScrollContainer?.nativeElement;
    if (!container) {
      return;
    }

    const saved = sessionStorage.getItem(this.scrollStorageKey);
    if (!saved) {
      return;
    }

    requestAnimationFrame(() => {
      container.scrollTop = Number(saved) || 0;
    });
  }

  private slugify(value: string): string {
    return value
      .normalize('NFD')
      .replace(/[\u0300-\u036f]/g, '')
      .toLowerCase()
      .replace(/[^a-z0-9\s-]/g, '')
      .trim()
      .replace(/\s+/g, '-')
      .replace(/-+/g, '-');
  }
}
