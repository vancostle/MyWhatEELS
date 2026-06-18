import { Component, input } from '@angular/core';
import { RouterLink } from '@angular/router';

@Component({
  selector: 'app-item',
  imports: [RouterLink],
  templateUrl: './item.html',
  styleUrl: './item.css',
})
export class Item {
  href = input<string>('Item Link');
  name = input<string>('Item Name');
  isActive = input<boolean>(false);
}
