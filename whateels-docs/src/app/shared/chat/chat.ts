import { Component, inject } from '@angular/core';
import { EmailAdmin } from './email-admin/email-admin';
import { EmailStatus } from './email-status/email-status';
import { ChatService } from '../services/chat.service';
import { EmailAdminService } from '../services/email-admin.service';
import { EmailStatusService } from '../services/email-status.service';

@Component({
  selector: 'app-chat',
  standalone: true,
  imports: [EmailAdmin, EmailStatus],
  templateUrl: './chat.html',
  styleUrl: './chat.css',
})
export class Chat {
  private readonly chatService = inject(ChatService);
  private readonly emailAdminService = inject(EmailAdminService);
  private readonly emailStatusService = inject(EmailStatusService);

  isChatOpen(): boolean {
    return this.chatService.isOpen();
  }

  toggleChat(): void {
    this.chatService.toggle();
  }

  isEmailAdminOpen(): boolean {
    return this.emailAdminService.isOpen();
  }

  isEmailStatusOpen(): boolean {
    return this.emailStatusService.isOpen();
  }

  toggleEmailAdmin(): void {
    this.emailAdminService.toggle();
  }
}
