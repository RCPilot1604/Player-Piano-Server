// src/app/services/socket.service.ts
import { Injectable } from '@angular/core';
import { Socket } from "ngx-socket-io";
import { Observable } from 'rxjs';

@Injectable()
export class WebsocketService {
  constructor(private socket:Socket) {
  }

  emit(event: string, data: any) {
    this.socket.emit(event, data);
  }

  fromEvent(event: string): Observable<any>{
    return this.socket.fromEvent(event);
  }
  disconnect() {
    this.socket.disconnect();
  }
}