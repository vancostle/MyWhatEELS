import { Component, input } from '@angular/core';
import { Heading } from './heading/heading';
import { Item } from './item/item';

@Component({
  selector: 'app-section',
  imports: [Heading, Item],
  templateUrl: './section.html',
  styleUrl: './section.css',

})
export class Section {
  title = input<string>('Section Title');
  href = input<string>('/');
  items = input<{ name: string; href: string; isActive?: boolean }[]>([
    { name: 'Item 1', href: '#', isActive: true },
    { name: 'Item 2', href: '#'},
  ]);
}
