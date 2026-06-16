import {
  Component,
  HostBinding,
  computed,
  inject,
} from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { toSignal } from '@angular/core/rxjs-interop';
import { FormControl, ReactiveFormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { SearchModalService } from '../services/search-modal.service';
import { SlugifyPipe } from '../pipes/slugify.pipe';
import { catchError, map, of, startWith, timeout } from 'rxjs';

type PagesIndexResponse = {
  categories: Array<{
    name: string;
    pages: string[];
  }>;
};

type SearchResult = {
  category: string;
  page: string;
  href: string;
};

@Component({
  selector: 'app-search-modal',
  imports: [ReactiveFormsModule, RouterLink],
  providers: [SlugifyPipe],
  templateUrl: './search-modal.html',
  styleUrl: './search-modal.css',
})
export class SearchModal {
  private readonly http = inject(HttpClient);
  private readonly slugifyPipe = inject(SlugifyPipe);

  readonly searchQuery = new FormControl('', { nonNullable: true });
  readonly searchModalService = inject(SearchModalService);
  private readonly allResults = toSignal(
    this.http.get<PagesIndexResponse>('assets/pages-index.json').pipe(
      timeout(5000),
      map((response) =>
        response.categories.flatMap((category) =>
          category.pages.map((page) => ({
            category: this.toTitleCase(category.name),
            page: this.toTitleCase(page),
            href: `/${this.slugifyPipe.transform(category.name)}/${this.slugifyPipe.transform(page)}`,
          }))
        )
      ),
      catchError(() => of([] as SearchResult[]))
    ),
    { initialValue: [] }
  );
  private readonly normalizedQuery = toSignal(
    this.searchQuery.valueChanges.pipe(
      startWith(this.searchQuery.value),
      map((query) => this.normalizeSearchTerm(query))
    ),
    { initialValue: '' }
  );
  readonly searchResults = computed(() => {
    const query = this.normalizedQuery();
    const results = this.allResults();

    if (!query) {
      return [];
    }

    return results.filter((result) => {
      const page = this.normalizeSearchTerm(result.page);
      const category = this.normalizeSearchTerm(result.category);
      return page.includes(query) || category.includes(query);
    });
  });
  readonly hasQuery = computed(() => this.normalizedQuery().length > 0);
  readonly hasNoResults = computed(() => this.hasQuery() && this.searchResults().length === 0);

  @HostBinding('class.active')
  get isActive(): boolean {
    return this.searchModalService.isOpen();
  }

  trackByHref(_: number, result: SearchResult): string {
    return result.href;
  }

  private normalizeSearchTerm(value: string): string {
    return value
      .normalize('NFD')
      .replace(/[\u0300-\u036f]/g, '')
      .toLowerCase()
      .trim();
  }

  private toTitleCase(value: string): string {
    return value
      .replace(/[_.-]+/g, ' ')
      .trim()
      .replace(/\b\w/g, (letter) => letter.toUpperCase());
  }
}
