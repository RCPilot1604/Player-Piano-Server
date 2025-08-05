import { Component, Output, Input, EventEmitter } from '@angular/core';
import { IPianoKey } from './ipiano-key';
import { NgIf, NgFor } from '@angular/common';
import { environment } from '../../environments/environment';

@Component({
  selector: 'keyboard',
  imports: [NgIf, NgFor],
  templateUrl: './keyboard.component.html',
  styleUrls: ['./keyboard.component.css']
})
export class KeyboardComponent{
  @Input() keyColors: { key: number, colour: string } [] = [];
  @Output() keyPressed = new EventEmitter<number>();
  pianoKeys: IPianoKey[] = [];
  environment = environment;
  constructor() {
  }

  initializePianoKeys(): void {
    this.pianoKeys = [
      { whiteKeyId: 21 },
      { whiteKeyId: 22, blackKeyId: 23 },
      { whiteKeyId: 24 },
      { whiteKeyId: 26, blackKeyId: 25 },
      { whiteKeyId: 28, blackKeyId: 27 },
      { whiteKeyId: 29 },
      { whiteKeyId: 31, blackKeyId: 30 },
      { whiteKeyId: 33, blackKeyId: 32 },
      { whiteKeyId: 35, blackKeyId: 34 },
      { whiteKeyId: 36 },
      { whiteKeyId: 38, blackKeyId: 37 },
      { whiteKeyId: 40, blackKeyId: 39 },
      { whiteKeyId: 41 },
      { whiteKeyId: 43, blackKeyId: 42 },
      { whiteKeyId: 45, blackKeyId: 44 },
      { whiteKeyId: 47, blackKeyId: 46 },
      { whiteKeyId: 48 },
      { whiteKeyId: 50, blackKeyId: 49 },
      { whiteKeyId: 52, blackKeyId: 51 },
      { whiteKeyId: 53 },
      { whiteKeyId: 55, blackKeyId: 54 },
      { whiteKeyId: 57, blackKeyId: 56 },
      { whiteKeyId: 59, blackKeyId: 58 },
      { whiteKeyId: 60 },
      { whiteKeyId: 62, blackKeyId: 61 },
      { whiteKeyId: 64, blackKeyId: 63 },
      { whiteKeyId: 65 },
      { whiteKeyId: 67, blackKeyId: 66 },
      { whiteKeyId: 69, blackKeyId: 68 },
      { whiteKeyId: 71, blackKeyId: 70 },
      { whiteKeyId: 72 },
      { whiteKeyId: 74, blackKeyId: 73 },
      { whiteKeyId: 76, blackKeyId: 75 },
      { whiteKeyId: 77 },
      { whiteKeyId: 79, blackKeyId: 78 },
      { whiteKeyId: 81, blackKeyId: 80 },
      { whiteKeyId: 83, blackKeyId: 82 },
      { whiteKeyId: 84 },
      { whiteKeyId: 86, blackKeyId: 85 },
      { whiteKeyId: 88, blackKeyId: 87 },
      { whiteKeyId: 89 },
      { whiteKeyId: 91, blackKeyId: 90 },
      { whiteKeyId: 93, blackKeyId: 92 },
      { whiteKeyId: 95, blackKeyId: 94 },
      { whiteKeyId: 96 },
      { whiteKeyId: 98, blackKeyId: 97 },
      { whiteKeyId: 100, blackKeyId: 99 },
      { whiteKeyId: 101 },
      { whiteKeyId: 103, blackKeyId: 102 },
      { whiteKeyId: 105, blackKeyId: 104 },
      { whiteKeyId: 107, blackKeyId: 106 },
      { whiteKeyId: 108 }
    ];
  }
  ngOnInit() {
    this.initializePianoKeys();
  }
  keyPress(keyId: number): void {
    this.keyPressed.emit(keyId);
  }
  getColor(keyId: number): string {
    const key = this.keyColors.find(k => k.key === keyId);
    return key ? key.colour : '';
  }
}
