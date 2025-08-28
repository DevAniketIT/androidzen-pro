import { WebSocketMessage } from '../types';

export type WebSocketEventHandler = (message: WebSocketMessage) => void;

class WebSocketService {
  private socket: WebSocket | null = null;
  private url: string;
  private reconnectAttempts: number = 0;
  private maxReconnectAttempts: number = 5;
  private reconnectInterval: number = 5000;
  private isReconnecting: boolean = false;
  private heartbeatInterval: number = 30000;
  private heartbeatTimer: NodeJS.Timeout | null = null;
  private eventHandlers: Map<string, WebSocketEventHandler[]> = new Map();

  constructor() {
    this.url = process.env.REACT_APP_WS_URL || 'ws://localhost:8000/ws';
  }

  connect(token?: string): Promise<void> {
    return new Promise((resolve, reject) => {
      try {
        const wsUrl = token ? `${this.url}?token=${token}` : this.url;
        this.socket = new WebSocket(wsUrl);

        this.socket.onopen = () => {
          console.log('WebSocket connected');
          this.reconnectAttempts = 0;
          this.isReconnecting = false;
          this.startHeartbeat();
          this.emit('connection', {
            type: 'CONNECTION',
            data: { connected: true },
            timestamp: new Date().toISOString(),
          });
          resolve();
        };

        this.socket.onmessage = (event) => {
          try {
            const message: WebSocketMessage = JSON.parse(event.data);
            this.handleMessage(message);
          } catch (error) {
            console.error('Error parsing WebSocket message:', error);
          }
        };

        this.socket.onclose = (event) => {
          console.log('WebSocket disconnected:', event.code, event.reason);
          this.stopHeartbeat();
          this.emit('disconnection', {
            type: 'DISCONNECTION',
            data: { connected: false },
            timestamp: new Date().toISOString(),
          });

          if (!this.isReconnecting && event.code !== 1000) {
            this.attemptReconnect();
          }
        };

        this.socket.onerror = (error) => {
          console.error('WebSocket error:', error);
          reject(error);
        };
      } catch (error) {
        reject(error);
      }
    });
  }

  private handleMessage(message: WebSocketMessage) {
    // Handle different message types
    switch (message.type) {
      case 'DEVICE_CONNECTED':
      case 'DEVICE_DISCONNECTED':
      case 'DEVICE_UPDATE':
        this.emit('device', message);
        break;
      case 'COMMAND_STATUS':
        this.emit('command', message);
        break;
      case 'SYSTEM_ALERT':
        this.emit('alert', message);
        break;
      case 'AI_INSIGHT':
        this.emit('ai', message);
        break;
      default:
        this.emit('message', message);
    }

    // Emit to all handlers
    this.emit('*', message);
  }

  private attemptReconnect() {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error('Max reconnection attempts reached');
      return;
    }

    this.isReconnecting = true;
    this.reconnectAttempts++;

    console.log(
      `Attempting to reconnect (${this.reconnectAttempts}/${this.maxReconnectAttempts})...`
    );

    setTimeout(() => {
      const token = localStorage.getItem('authToken');
      this.connect(token || undefined).catch((error) => {
        console.error('Reconnection failed:', error);
        this.attemptReconnect();
      });
    }, this.reconnectInterval * this.reconnectAttempts);
  }

  private startHeartbeat() {
    this.heartbeatTimer = setInterval(() => {
      if (this.socket?.readyState === WebSocket.OPEN) {
        this.send({
          type: 'PING',
          data: {},
          timestamp: new Date().toISOString(),
        });
      }
    }, this.heartbeatInterval);
  }

  private stopHeartbeat() {
    if (this.heartbeatTimer) {
      clearInterval(this.heartbeatTimer);
      this.heartbeatTimer = null;
    }
  }

  send(message: WebSocketMessage) {
    if (this.socket?.readyState === WebSocket.OPEN) {
      this.socket.send(JSON.stringify(message));
    } else {
      console.warn('WebSocket is not connected');
    }
  }

  disconnect() {
    this.stopHeartbeat();
    if (this.socket) {
      this.socket.close(1000, 'Client disconnect');
      this.socket = null;
    }
    this.isReconnecting = false;
    this.reconnectAttempts = 0;
  }

  // Event handling
  on(event: string, handler: WebSocketEventHandler) {
    if (!this.eventHandlers.has(event)) {
      this.eventHandlers.set(event, []);
    }
    this.eventHandlers.get(event)!.push(handler);
  }

  off(event: string, handler: WebSocketEventHandler) {
    const handlers = this.eventHandlers.get(event);
    if (handlers) {
      const index = handlers.indexOf(handler);
      if (index > -1) {
        handlers.splice(index, 1);
      }
    }
  }

  private emit(event: string, message: WebSocketMessage) {
    const handlers = this.eventHandlers.get(event);
    if (handlers) {
      handlers.forEach((handler) => {
        try {
          handler(message);
        } catch (error) {
          console.error('Error in WebSocket event handler:', error);
        }
      });
    }
  }

  // Utility methods
  isConnected(): boolean {
    return this.socket?.readyState === WebSocket.OPEN;
  }

  getConnectionState(): number {
    return this.socket?.readyState || WebSocket.CLOSED;
  }

  getConnectionStateString(): string {
    const state = this.getConnectionState();
    switch (state) {
      case WebSocket.CONNECTING:
        return 'connecting';
      case WebSocket.OPEN:
        return 'open';
      case WebSocket.CLOSING:
        return 'closing';
      case WebSocket.CLOSED:
        return 'closed';
      default:
        return 'unknown';
    }
  }

  // Device-specific methods
  subscribeToDevice(deviceId: string) {
    this.send({
      type: 'SUBSCRIBE_DEVICE',
      data: { deviceId },
      timestamp: new Date().toISOString(),
    });
  }

  unsubscribeFromDevice(deviceId: string) {
    this.send({
      type: 'UNSUBSCRIBE_DEVICE',
      data: { deviceId },
      timestamp: new Date().toISOString(),
    });
  }

  // Command execution
  executeCommand(deviceId: string, command: string, type: string = 'CUSTOM') {
    this.send({
      type: 'EXECUTE_COMMAND',
      data: {
        deviceId,
        command,
        commandType: type,
      },
      timestamp: new Date().toISOString(),
    });
  }
}

export const webSocketService = new WebSocketService();
export default webSocketService;
