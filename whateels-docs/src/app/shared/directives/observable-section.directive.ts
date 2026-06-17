import {
  Directive,
  ElementRef,
  inject,
  OnInit,
  OnDestroy,
} from '@angular/core';
import { ObservableSectionService } from '../services/observable-section.service';

@Directive({
  selector: '[appObservableSection]',
  standalone: true,
})
export class ObservableSectionDirective implements OnInit, OnDestroy {
  private el = inject(ElementRef<HTMLElement>);
  private observableService = inject(ObservableSectionService);

  ngOnInit() {
    if (this.el.nativeElement.id) {
      this.observableService.registerElement(this.el.nativeElement);
    }
  }

  ngOnDestroy() {
    this.observableService.unregisterElement(this.el.nativeElement);
  }
}
