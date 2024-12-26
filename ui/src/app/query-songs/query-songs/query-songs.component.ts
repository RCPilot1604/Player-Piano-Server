import { Component, inject } from '@angular/core';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatToolbarModule } from '@angular/material/toolbar';
import { MatSelect } from '@angular/material/select';
import { MatButton } from '@angular/material/button';
@Component({
  selector: 'app-query-songs',
  imports: [ MatToolbarModule, MatFormFieldModule, MatInputModule ],
  template: `
    <mat-toolbar color="primary" id="search-bar">
    <mat-toolbar-row>
      <mat-form-field id="search-field">
        <mat-label>Search</mat-label>
        <input matInput type="text">
      </mat-form-field>
      <mat-form-field id="category-field">
        <mat-label>Category</mat-label>
        <mat-select>
          <mat-option>Category 1</mat-option>
          <mat-option>Category 2</mat-option>
        </mat-select>
      </mat-form-field>
    </mat-toolbar-row>
  `,
  styleUrl: './query-songs.component.css'
})
export class QuerySongsComponent {

}
