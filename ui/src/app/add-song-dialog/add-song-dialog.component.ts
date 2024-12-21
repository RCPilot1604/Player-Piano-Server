import { Component, EventEmitter, Output, OnInit } from '@angular/core';
import { FormControl, FormGroup, ReactiveFormsModule} from '@angular/forms';
import { MatIconModule } from '@angular/material/icon';
import { Validators } from '@angular/forms';
import { SongsService } from '../songs.service';
import { CategoryService } from '../categories.service';
import { MatDialogRef } from '@angular/material/dialog';
import { MatSnackBar } from '@angular/material/snack-bar';
import { MatIcon } from '@angular/material/icon';
import { NgIf, NgForOf } from '@angular/common';

@Component({
  selector: 'app-add-song-dialog',
  imports: [ReactiveFormsModule, MatIconModule, NgIf, NgForOf, MatIcon],
  template: `
    <div class="dialog-overlay" (click)="onCancel()"></div>
    <div class="dialog">
      <h2>Add New Song</h2>
      <form [formGroup]="newSongForm" (submit)="addNewSong()">
        <label for="title"> Title: </label>
        <input type="text" id="title" formControlName="title" required>
        <label for="composer"> Composer: </label>
        <input type="text" id="composer" formControlName="composer" required>
        <label for="category"> Category: </label>
        <select id="category" formControlName="category" (onclick)="refreshCategories()" required>
          <option *ngFor="let category of categories" [value]="category">{{ category }}</option>
        </select>
        <label for="midiFile"> Upload MIDI File: </label>
        <input type="file" class="file-input" formControlName="midiFile" (change)="onFileSelected($event)" #fileUpload>
        <div class="file-upload"> {{fileName || "No file uploaded yet."}}
          <button mat-mini-fab color="primary" class="upload-btn" (click)="fileUpload.click()">
            <mat-icon>attach_file</mat-icon>
          </button>
        </div>
        <div *ngIf="formError" class="error-box">{{ formError }}</div>
        <div *ngIf="fileError" class="error-box">{{ fileError }}</div>
        <div class="dialog-actions">
          <button type="button" (click)="onCancel()">Cancel</button>
          <button type="submit">Add Song</button>
        </div>
      </form>
    </div>
  `,
  styleUrls: ['./add-song-dialog.component.css']
})
export class AddSongDialogComponent {
  newSongForm = new FormGroup(
    {
      title: new FormControl(''),
      composer: new FormControl(''),
      category: new FormControl(''),
      midiFile: new FormControl(''),
    }
  )

  categories: string[] = [];
  fileName = '';
  formData = new FormData(); 
  selectedFile: File | null = null;
  fileError: string | null = null;
  formError: string | null = null;
  
  @Output() songAdded = new EventEmitter();

  constructor( 
    private songsService: SongsService,
    private categoryService: CategoryService,
    private dialogRef: MatDialogRef<AddSongDialogComponent>,
    private snackBar: MatSnackBar
  ) {}

  ngOnInit() {
    this.refreshCategories();
  }

  refreshCategories(){
    this.categoryService.getCategories().subscribe(data => {
      this.categories = data;
    });
  }
  addNewSong(): void{
    if (this.newSongForm.valid && this.selectedFile) {
      this.formError = null; // Clear any previous error
      this.formData.append('title', this.newSongForm.value.title ?? '');
      this.formData.append('composer', this.newSongForm.value.composer ?? '');
      this.formData.append('category', this.newSongForm.value.category ?? '');
      this.formData.append('midiPath', this.fileName ?? '');
      this.formData.append('midiFile', this.selectedFile);
      this.songsService.addSong(this.formData).subscribe(() => {
        this.snackBar.open('Song added successfully!', 'Close', {
          duration: 3000,
        });
        this.songAdded.emit();
        this.dialogRef.close();
        this.fileName = ''; //reset the file name after the song is added
      }, error => {
        this.formError = "Error adding song: " + error;
      });
      //console.table(Object.fromEntries(this.formData));
    } else {
      this.formError = "Please fill out all fields and upload a MIDI file.";
    }
  }

  onCancel(): void {
    this.dialogRef.close();
  }

  onFileSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    if (input.files && input.files[0]) {
      const file: File = input.files[0];
      const fileExtension = file.name.split('.').pop()?.toLowerCase();
      if (fileExtension === 'mid' || fileExtension === 'midi') {
        this.fileName = file.name;
        this.selectedFile = file;
        this.fileError = null; // Clear any previous error
      } else {
        this.fileError = 'Invalid file type. Only .mid and .midi files are allowed.';
        input.value = '';
      }
    }
  }
}

