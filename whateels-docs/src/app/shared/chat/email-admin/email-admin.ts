import { Component, inject } from '@angular/core';
import { ReactiveFormsModule, FormBuilder, Validators } from '@angular/forms';
import { EmailAdminService } from '../../services/email-admin.service';
import { ChatService } from '../../services/chat.service';
import { EmailStatusService } from '../../services/email-status.service';
import emailjs from '@emailjs/browser';

type EmailJsError = {
  status?: number;
  text?: string;
  message?: string;
};

@Component({
  selector: 'app-email-admin',
  imports: [ReactiveFormsModule],
  templateUrl: './email-admin.html',
  styleUrl: './email-admin.css',
})
export class EmailAdmin {
  private readonly formBuilder = inject(FormBuilder);
  private readonly chatService = inject(ChatService);
  private readonly emailAdminService = inject(EmailAdminService);
  private readonly emailStatusService = inject(EmailStatusService);
  private isSending = false;

  private readonly serviceId = 'service_1g2l90b';
  private readonly templateId = 'template_ns19wkj';
  private readonly publicKey = 'JyiNTj9AATdJvPPB1';

  closeChat(): void {
    this.chatService.close();
  }

  readonly emailForm = this.formBuilder.nonNullable.group({
    name: ['', [Validators.required, Validators.minLength(2), Validators.pattern(/^[A-Za-zÀ-ÿ' -]+$/)]],
    email: ['', [Validators.required, Validators.email]],
    message: ['', [Validators.required, Validators.minLength(10), Validators.maxLength(1000)]],
  });

  async sendEmail(event: SubmitEvent): Promise<void> {
    event.preventDefault();

    if (this.isSending) {
      return;
    }

    if (this.emailForm.invalid) {
      this.emailForm.markAllAsTouched();
      return;
    }

    const { name, email, message } = this.emailForm.getRawValue();
    this.isSending = true;
    this.emailAdminService.close();
    this.emailStatusService.showLoading();

    try {
      const response = await emailjs.send(
        this.serviceId,
        this.templateId,
        {
          from_name: name,
          from_email: email,
          message,
          user_email: email,
          name: name,
        },
        this.publicKey
      );

      if (response.status === 200) {
        this.emailStatusService.showSuccess();
        this.emailForm.reset();
      } else {
        this.emailStatusService.showError();
        console.error(`EmailJS failed with status ${response.status}.`);
      }
    } catch (error: unknown) {
      const emailJsError = error as EmailJsError;
      const reason = emailJsError.text ?? emailJsError.message ?? 'Unknown error';
      const statusInfo = emailJsError.status ? ` (status ${emailJsError.status})` : '';

      this.emailStatusService.showError();
      console.error('EmailJS send failed:', error);
      console.error(`Email failed${statusInfo}: ${reason}`);
    } finally {
      this.isSending = false;
    }
  }
}
