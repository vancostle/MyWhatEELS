import { Component, input } from '@angular/core';
import { RouterLink } from '@angular/router';

@Component({
  selector: 'app-heading',
  imports: [RouterLink],
  templateUrl: './heading.html',
  styleUrl: './heading.css',
})
export class Heading {
  href = input<string>('/');
}
