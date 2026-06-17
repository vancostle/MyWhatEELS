import { Component, inject } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { HttpClient } from '@angular/common/http';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { catchError, map, of, switchMap, timeout } from 'rxjs';
import { ObservableSectionService } from '../services/observable-section.service';

@Component({
  selector: 'app-right-sidebar',
  imports: [RouterLink],
  templateUrl: './right-sidebar.html',
  styleUrl: './right-sidebar.css',
})
export class RightSidebar {
  private readonly route = inject(ActivatedRoute);
  private readonly http = inject(HttpClient);
  private observableService = inject(ObservableSectionService);

  readonly sections = toSignal(
    this.route.paramMap.pipe(
      map((params) => {
        const categorySlug = this.normalizePathSegment(params.get('category')) ?? 'introduction';
        const pageSlug = this.normalizePathSegment(params.get('page')) ?? 'whateels';
        const category = this.routeSegmentToFileName(categorySlug);
        const page = this.routeSegmentToFileName(pageSlug);

        return `assets/pages/${category}/${page}.md`;
      }),
      switchMap((src) =>
        this.http.get(src, { responseType: 'text' }).pipe(
          timeout(10000),
          map((markdown) => this.extractH2Sections(markdown)),
          catchError(() => of([]))
        )
      )
    ),
    { initialValue: [] }
  );

  activeSectionId = this.observableService.activeSectionId;

  isActive(slug: string): boolean {
    return this.activeSectionId() === slug;
  }

  private extractH2Sections(markdown: string): Array<{ title: string; slug: string }> {
    const headingMatches = markdown.matchAll(/^##\s+(.+)$/gm);

    return [...headingMatches]
      .map((match) => {
        const title = this.cleanHeadingText(match[1]);
        return {
          title,
          slug: this.slugify(title),
        };
      })
      .filter((section) => section.title.length > 0);
  }

  private cleanHeadingText(value: string): string {
    return value
      .replace(/\[(.*?)\]\((.*?)\)/g, '$1')
      .replace(/[`*_~#]/g, '')
      .trim();
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

  private routeSegmentToFileName(value: string): string {
    return value.replace(/-/g, ' ');
  }
}
