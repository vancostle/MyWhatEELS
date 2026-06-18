import { Doc } from './doc/doc';
import { Routes } from '@angular/router';

export const routes: Routes = [
  { path: '', pathMatch: 'full', redirectTo: 'introduction/whateels' },
  { path: ':category/:page', component: Doc }
];