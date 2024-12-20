import { Component, Input} from '@angular/core';
import { SongEntry } from '../song-entry';
import { NgIf } from '@angular/common';

@Component({
  selector: 'app-current-song',
  imports: [NgIf],
  templateUrl: './current-song.component.html',
  styleUrl: './current-song.component.css'
})
export class CurrentSongComponent {
  @Input () song: SongEntry | null = null;
}
