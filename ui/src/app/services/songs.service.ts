import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { map } from 'rxjs/operators';
import { SongEntry } from '../models/song-entry.model';
import { environment } from '../../environments/environment';
@Injectable({
  providedIn: 'root'
})
export class SongsService {
  host = `${environment.httpApi}/api/crud/`;
  constructor(private http: HttpClient) { }
  getSong() {
    return this.http.get<SongEntry[]>(this.host).pipe(map((res) => res));
  }
  addSong(formData: any) {
    return this.http.post(this.host, formData);
  }
  deleteSong(id: number) {
    return this.http.delete(`${this.host}${id}/`);
  }
}
