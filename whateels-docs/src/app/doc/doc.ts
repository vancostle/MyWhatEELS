import { Component } from '@angular/core';

import { Header } from '../shared/header/header';
import { Main } from '../shared/main/main';
import { LeftSidebar } from '../shared/left-sidebar/left-sidebar';
import { SearchModal } from '../shared/search-modal/search-modal';
import { Chat } from '../shared/chat/chat';
// import { Modal } from '../shared/modal/modal';

@Component({
  selector: 'app-doc',
  standalone: true,
  imports: [Header, Main, LeftSidebar, SearchModal, Chat],
  templateUrl: './doc.html',
  styleUrl: './doc.css',
})
export class Doc { }