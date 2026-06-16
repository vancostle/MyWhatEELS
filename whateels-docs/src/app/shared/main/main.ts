import { isPlatformBrowser } from '@angular/common';
import { Component, computed, ElementRef, inject, PLATFORM_ID } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { HttpClient } from '@angular/common/http';
import { ActivatedRoute } from '@angular/router';
import { catchError, map, of, scan, startWith, switchMap, timeout } from 'rxjs';
import { RightSidebar } from '../right-sidebar/right-sidebar';
import { Footer } from '../footer/footer';
import { Divider } from '../divider/divider';
import { MarkdownComponent } from 'ngx-markdown';
import { ObservableSectionService } from '../services/observable-section.service';

type MarkdownState = {
  isLoading: boolean;
  title: string;
  content: string;
};

type MarkdownEvent =
  | { type: 'loading' }
  | { type: 'loaded'; title: string; content: string }
  | { type: 'error' };

@Component({
  selector: 'app-main',
  imports: [RightSidebar, Footer, Divider, MarkdownComponent],
  templateUrl: './main.html',
  styleUrl: './main.css',
})
export class Main {
  private readonly platformId = inject(PLATFORM_ID);
  private readonly hostElement = inject(ElementRef<HTMLElement>);
  private readonly http = inject(HttpClient);
  private readonly route = inject(ActivatedRoute);
  private readonly observableSectionService = inject(ObservableSectionService);
  private readonly markdownState = toSignal(
    this.route.paramMap.pipe(
      map((params) => {
        const categorySlug = this.normalizePathSegment(params.get('category')) ?? 'introduction';
        const pageSlug = this.normalizePathSegment(params.get('page')) ?? 'whateels';
        const category = this.routeSegmentToFileName(categorySlug);
        const page = this.routeSegmentToFileName(pageSlug);

        return {
          page,
          src: `assets/pages/${category}/${page}.md`,
        };
      }),
      switchMap(({ page, src }) => {
        const title = this.formatFileName(page);

        return this.http.get(src, { responseType: 'text' }).pipe(
          timeout(10000),
          map((content): MarkdownEvent => ({ type: 'loaded', title, content })),
          startWith({ type: 'loading' } as MarkdownEvent),
          catchError(() => of({ type: 'error' } as MarkdownEvent))
        );
      }),
      scan<MarkdownEvent, MarkdownState>((state, event) => {
        if (event.type === 'loading') {
          return { ...state, isLoading: true };
        }

        if (event.type === 'error') {
          return { ...state, isLoading: false };
        }

        return {
          isLoading: false,
          title: event.title,
          content: event.content,
        };
      }, { isLoading: true, title: '', content: '' })
    ),
    { initialValue: { isLoading: true, title: '', content: '' } }
  );

  readonly isMarkdownLoading = computed(() => this.markdownState().isLoading);
  readonly markdownContent = computed(() => this.markdownState().content);
  readonly pageTitle = computed(() => this.markdownState().title);
  private lastSectionContent = '';

  onMarkdownReady(): void {
    const content = this.markdownContent();

    if (!content || content === this.lastSectionContent) {
      return;
    }

    this.lastSectionContent = content;
    this.assignSectionIds();
  }

  onMarkdownError(): void {}

  private assignSectionIds(): void {
    if (!isPlatformBrowser(this.platformId)) {
      return;
    }

    const markdownRoot = this.hostElement.nativeElement.querySelector('.markdown-content');
    if (!markdownRoot) {
      return;
    }

    const headings = Array.from(markdownRoot.querySelectorAll('h2')) as HTMLElement[];
    headings.forEach((heading) => {
      const text = heading.textContent?.trim() ?? '';
      heading.id = this.slugify(text);
    });

    this.observableSectionService.observeElements(headings.filter((heading) => heading.id.length > 0));
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

  private normalizePathSegment(value: string | null): string | null {
    if (!value) {
      return null;
    }

    return /^[A-Za-z0-9_-]+$/.test(value) ? value : null;
  }

  private formatFileName(value: string): string {
    return value
      .replace(/[_.-]+/g, ' ')
      .trim()
      .replace(/\b\w/g, (letter) => letter.toUpperCase());
  }

  private routeSegmentToFileName(value: string): string {
    return value.replace(/-/g, ' ');
  }
}