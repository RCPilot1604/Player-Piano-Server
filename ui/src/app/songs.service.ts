import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { map } from 'rxjs/operators';
import { SongEntry } from './song-entry';

@Injectable({
  providedIn: 'root'
})
export class SongsService {
  host = "http://localhost:3000/api/crud";
  constructor(private http: HttpClient) { }
  getSong() {
    return this.http.get<SongEntry[]>(this.host).pipe(map((res) => res));
  }
  addSong(formData: FormData) {
    return this.http.post(this.host, formData);
  }
  deleteSong(id: number) {
    return this.http.delete(`${this.host}/${id}`);
  }
}
