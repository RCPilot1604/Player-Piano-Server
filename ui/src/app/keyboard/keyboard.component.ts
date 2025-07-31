import { Component, Output, Input, EventEmitter } from '@angular/core';
import { IPianoKey } from './ipiano-key';
@Component({
  selector: 'keyboard',
  imports: [],
  templateUrl: './keyboard.component.html',
  styleUrls: ['./keyboard.component.css']
})
export class KeyboardComponent {
  @Output() keyPressed = new EventEmitter<number>();
  @Input() keyActivated: { key: number, colour: string }[] = [];
  pianoKeys: IPianoKey[] = [];

  constructor() {
    this.initializePianoKeys();
  }

  initializePianoKeys(): void {
    this.pianoKeys = [
      { whiteKeyId: 21 },
      { whiteKeyId: 23, blackKeyId: 22 },
      { whiteKeyId: 25, blackKeyId: 24 },
      { whiteKeyId: 26 },
      { whiteKeyId: 28, blackKeyId: 27 },
      { whiteKeyId: 30, blackKeyId: 29 },
      { whiteKeyId: 32, blackKeyId: 31 },
      { whiteKeyId: 33 },
      { whiteKeyId: 35, blackKeyId: 34 },
      { whiteKeyId: 37, blackKeyId: 36 },
      { whiteKeyId: 38 },
      { whiteKeyId: 40, blackKeyId: 39 },
      { whiteKeyId: 42, blackKeyId: 41 },
      { whiteKeyId: 44, blackKeyId: 43 },
      { whiteKeyId: 45 },
      { whiteKeyId: 47, blackKeyId: 46 },
      { whiteKeyId: 49, blackKeyId: 48 },
      { whiteKeyId: 50 },
      { whiteKeyId: 52, blackKeyId: 51 },
      { whiteKeyId: 54, blackKeyId: 53 },
      { whiteKeyId: 56, blackKeyId: 55 },
      { whiteKeyId: 57 },
      { whiteKeyId: 59, blackKeyId: 58 },
      { whiteKeyId: 61, blackKeyId: 60 },
      { whiteKeyId: 63, blackKeyId: 62 },
      { whiteKeyId: 64 },
      { whiteKeyId: 66, blackKeyId: 65 },
      { whiteKeyId: 68, blackKeyId: 67 },
      { whiteKeyId: 69 },
      { whiteKeyId: 71, blackKeyId: 70 },
      { whiteKeyId: 73, blackKeyId: 72 },
      { whiteKeyId: 75, blackKeyId: 74 },
      { whiteKeyId: 76 },
      { whiteKeyId: 78, blackKeyId: 77 },
      { whiteKeyId: 80, blackKeyId: 79 },
      { whiteKeyId: 81 },
      { whiteKeyId: 83, blackKeyId: 82 },
      { whiteKeyId: 85, blackKeyId: 84 },
      { whiteKeyId: 87, blackKeyId: 86 },
      { whiteKeyId: 88 },
      { whiteKeyId: 90, blackKeyId: 89 },
      { whiteKeyId: 92, blackKeyId: 91 },
      { whiteKeyId: 93 },
      { whiteKeyId: 95, blackKeyId: 94 },
      { whiteKeyId: 97, blackKeyId: 96 },
      { whiteKeyId: 99, blackKeyId: 98 },
      { whiteKeyId: 100 },
      { whiteKeyId: 102, blackKeyId: 101 },
      { whiteKeyId: 104, blackKeyId: 103 },
      { whiteKeyId: 105 },
      { whiteKeyId: 107, blackKeyId: 106 },
      { whiteKeyId: 108 }
    ];
  }

  keyPress(keyId: number): void {
    this.keyPressed.emit(keyId);
  }
  getColor(keyId: number): string {
    const key = this.keyActivated.find(k => k.key === keyId);
    return key ? key.colour : 'white';
  }
}
