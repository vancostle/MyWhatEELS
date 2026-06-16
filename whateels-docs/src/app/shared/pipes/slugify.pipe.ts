import { Pipe, PipeTransform } from '@angular/core';

@Pipe({
  name: 'slugify',
  standalone: true,
})
export class SlugifyPipe implements PipeTransform {
  transform(value: string): string {
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
