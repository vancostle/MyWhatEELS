import { Component, inject } from '@angular/core';
import { EmailAdminService } from '../../services/email-admin.service';
import { EmailStatusService } from '../../services/email-status.service';

@Component({
  selector: 'app-email-status',
  imports: [],
  templateUrl: './email-status.html',
  styleUrl: './email-status.css',
})
export class EmailStatus {
  private readonly emailAdminService = inject(EmailAdminService);
  readonly emailStatusService = inject(EmailStatusService);

  sendAnotherEmail(): void {
    this.emailStatusService.close();
    this.emailAdminService.open();
  }
}
