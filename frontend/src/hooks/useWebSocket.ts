import { useEffect, useCallback } from 'react';

import { webSocketService, WebSocketEventHandler } from '../services/websocket';
import { WebSocketMessage } from '../types';
import { STORAGE_KEYS } from '../utils/constants';

import { useAppStore } from './useAppStore';

export const useWebSocket = (enabled: boolean = true) => {
  const { setConnectionStatus, addNotification } = useAppStore();

  const connect = useCallback(async () => {
    if (!enabled) return;

    try {
      const token = localStorage.getItem(STORAGE_KEYS.AUTH_TOKEN);
      await webSocketService.connect(token || undefined);
      setConnectionStatus(true);
    } catch (error) {
      console.error('Failed to connect to WebSocket:', error);
      setConnectionStatus(false);
    }
  }, [enabled, setConnectionStatus]);

  const disconnect = useCallback(() => {
    webSocketService.disconnect();
    setConnectionStatus(false);
  }, [setConnectionStatus]);

  useEffect(() => {
    if (enabled) {
      connect();

      // Set up event handlers
      const handleConnection: WebSocketEventHandler = (_message) => {
        setConnectionStatus(true);
      };

      const handleDisconnection: WebSocketEventHandler = (_message) => {
        setConnectionStatus(false);
      };

      const handleSystemAlert: WebSocketEventHandler = (message) => {
        if (message.data) {
          addNotification({
            type: message.data.type || 'INFO',
            title: message.data.title || 'System Alert',
            message: message.data.message || '',
            deviceId: message.data.deviceId,
          });
        }
      };

      // Register event handlers
      webSocketService.on('connection', handleConnection);
      webSocketService.on('disconnection', handleDisconnection);
      webSocketService.on('alert', handleSystemAlert);

      return () => {
        // Cleanup event handlers
        webSocketService.off('connection', handleConnection);
        webSocketService.off('disconnection', handleDisconnection);
        webSocketService.off('alert', handleSystemAlert);
        disconnect();
      };
    }
  }, [enabled, connect, disconnect, setConnectionStatus, addNotification]);

  return {
    connect,
    disconnect,
    isConnected: webSocketService.isConnected(),
    connectionState: webSocketService.getConnectionStateString(),
    send: webSocketService.send.bind(webSocketService),
    on: webSocketService.on.bind(webSocketService),
    off: webSocketService.off.bind(webSocketService),
    subscribeToDevice: webSocketService.subscribeToDevice.bind(webSocketService),
    unsubscribeFromDevice: webSocketService.unsubscribeFromDevice.bind(webSocketService),
    executeCommand: webSocketService.executeCommand.bind(webSocketService),
  };
};

// Custom hook for device-specific WebSocket events
export const useDeviceWebSocket = (deviceId: string | null) => {
  const webSocket = useWebSocket();

  useEffect(() => {
    if (deviceId && webSocket.isConnected) {
      webSocket.subscribeToDevice(deviceId);

      return () => {
        webSocket.unsubscribeFromDevice(deviceId);
      };
    }
  }, [deviceId, webSocket, webSocket.isConnected]);

  const executeCommand = useCallback(
    (command: string, type?: string) => {
      if (deviceId) {
        webSocket.executeCommand(deviceId, command, type);
      }
    },
    [deviceId, webSocket]
  );

  return {
    ...webSocket,
    executeCommand,
  };
};

// Custom hook for listening to specific WebSocket events
export const useWebSocketEvent = (
  event: string,
  handler: WebSocketEventHandler,
  deps: any[] = []
) => {
  useEffect(() => {
    webSocketService.on(event, handler);

    return () => {
      webSocketService.off(event, handler);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [event, handler, ...deps]);
};

// Custom hook for real-time device updates
export const useDeviceUpdates = (callback: (message: WebSocketMessage) => void) => {
  const handleDeviceEvent: WebSocketEventHandler = useCallback(
    (message) => {
      callback(message);
    },
    [callback]
  );

  useWebSocketEvent('device', handleDeviceEvent, [callback]);
};

// Custom hook for command status updates
export const useCommandUpdates = (callback: (message: WebSocketMessage) => void) => {
  const handleCommandEvent: WebSocketEventHandler = useCallback(
    (message) => {
      callback(message);
    },
    [callback]
  );

  useWebSocketEvent('command', handleCommandEvent, [callback]);
};

// Custom hook for AI insights
export const useAIInsights = (callback: (message: WebSocketMessage) => void) => {
  const handleAIEvent: WebSocketEventHandler = useCallback(
    (message) => {
      callback(message);
    },
    [callback]
  );

  useWebSocketEvent('ai', handleAIEvent, [callback]);
};
