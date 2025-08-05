import { Component } from '@angular/core';
import { MatDialogRef, MAT_DIALOG_DATA } from '@angular/material/dialog';
import { MatButton } from '@angular/material/button';
import { MatIcon } from '@angular/material/icon';
import { Inject } from '@angular/core';
import { MatIconModule } from '@angular/material/icon';
export interface ConfirmDialogData {
  title?: string;
  message: string;
  confirmText?: string;
  cancelText?: string;
}
@Component({
  selector: 'app-confirm-dialog',
  template: `
    <div style="text-align:center; padding:24px;">
      <mat-icon color="warn" style="font-size:48px; height:48px; width:48px;">announcement</mat-icon>
      <h2>{{ data.title || 'Are you sure?' }}</h2>
      <p>{{ data.message }}</p>
      <div style="margin-top:24px; display:flex; justify-content:center; gap:24px;">
        <button mat-button style="background:white; font-weight:normal;" (click)="onCancel()">
          {{ data.cancelText || 'Cancel' }}
        </button>
        <button mat-raised-button color="warn" style="font-weight:bold;" (click)="onConfirm()">
          {{ data.confirmText || 'Delete' }}
        </button>
      </div>
    </div>
  `,
  styleUrls: ['./confirmation-dialog.css'],
  imports: [MatButton, MatIcon, MatIconModule],
})
export class ConfirmDialogComponent {
  constructor(
    private dialogRef: MatDialogRef<ConfirmDialogComponent>,
    @Inject(MAT_DIALOG_DATA) public data: ConfirmDialogData
  ) {}
  onCancel() { this.dialogRef.close(false); }
  onConfirm() { this.dialogRef.close(true); }
}