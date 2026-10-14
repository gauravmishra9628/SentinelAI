/**
 * SentinelAI WebSocket Service
 *
 * Centralized WebSocket connection manager with:
 * - Automatic reconnection with exponential backoff
 * - Event-based subscription model
 * - Graceful degradation (REST continues working if WS fails)
 * - Connection state reporting
 *
 * Usage:
 *   import { useWebSocket, wsService } from './services/websocket';
 *
 *   // In a React component:
 *   const { connectionState, lastMessage } = useWebSocket();
 *
 *   // Or use the service directly:
 *   wsService.on('alert', handleAlert);
 *   wsService.connect();
 */

import { API_BASE_URL } from './api';
import { useState, useEffect, useRef, useCallback } from 'react';

// WebSocket URL derived from the REST API base URL
const WS_PROTOCOL = API_BASE_URL.startsWith('https') ? 'wss' : 'ws';
const WS_BASE_URL = API_BASE_URL.replace(/^https?:\/\//, '');
const getWsUrl = () => {
  const token = window.localStorage.getItem('sentinel_access_token');
  return `${WS_PROTOCOL}://${WS_BASE_URL}/ws/alerts${token ? `?token=${encodeURIComponent(token)}` : ''}`;
};

// Reconnect configuration
const INITIAL_RECONNECT_DELAY_MS = 1000;
const MAX_RECONNECT_DELAY_MS = 30000;
const RECONNECT_MULTIPLIER = 1.5;

/** @typedef {'CONNECTING' | 'CONNECTED' | 'DISCONNECTED' | 'ERROR'} ConnectionState */

/**
 * SentinelAI WebSocket Service
 *
 * Singleton service that manages the WebSocket connection and distributes
 * incoming messages to registered event handlers.
 */
class WebSocketService {
  constructor() {
    /** @type {WebSocket|null} */
    this._ws = null;

    /** Event handlers: eventType -> Set of callback functions */
    this._handlers = new Map();

    /** Current connection state */
    this._connectionState = 'DISCONNECTED';

    /** Current reconnect delay in ms */
    this._reconnectDelay = INITIAL_RECONNECT_DELAY_MS;

    /** Timer handle for scheduled reconnect */
    this._reconnectTimer = null;

    /** Prevent concurrent connect attempts */
    this._connecting = false;

    /** Listener counts for debugging */
    this._listenerCounts = {};

    // Bind methods
    this.connect = this.connect.bind(this);
    this.disconnect = this.disconnect.bind(this);
    this._scheduleReconnect = this._scheduleReconnect.bind(this);
    this._clearReconnect = this._clearReconnect.bind(this);
    this._handleOpen = this._handleOpen.bind(this);
    this._handleMessage = this._handleMessage.bind(this);
    this._handleClose = this._handleClose.bind(this);
    this._handleError = this._handleError.bind(this);
  }

  // ── Public API ────────────────────────────────────────────────

  /**
   * Connect to the WebSocket server.
   * Idempotent: calling while already connected is a no-op.
   */
  connect() {
    if (this._ws && (this._ws.readyState === WebSocket.OPEN || this._ws.readyState === WebSocket.CONNECTING)) {
      return;
    }
    if (this._connecting) return;
    this._connecting = true;
    this._setState('CONNECTING');

    try {
      this._ws = new WebSocket(getWsUrl());
      this._ws.addEventListener('open', this._handleOpen);
      this._ws.addEventListener('message', this._handleMessage);
      this._ws.addEventListener('close', this._handleClose);
      this._ws.addEventListener('error', this._handleError);
    } catch (err) {
      console.warn('[WebSocket] Failed to create WebSocket:', err);
      this._setState('ERROR');
      this._connecting = false;
      this._scheduleReconnect();
    }
  }

  /**
   * Disconnect from the WebSocket server.
   * Idempotent: calling while already disconnected is a no-op.
   */
  disconnect() {
    this._clearReconnect();
    if (!this._ws) {
      this._setState('DISCONNECTED');
      this._connecting = false;
      return;
    }
    try {
      this._ws.removeEventListener('open', this._handleOpen);
      this._ws.removeEventListener('message', this._handleMessage);
      this._ws.removeEventListener('close', this._handleClose);
      this._ws.removeEventListener('error', this._handleError);
      this._ws.close(1000, 'Client disconnect');
    } catch (err) {
      console.warn('[WebSocket] Error during disconnect:', err);
    }
    this._ws = null;
    this._setState('DISCONNECTED');
    this._connecting = false;
  }

  /**
   * Register an event handler.
   *
   * @param {string} eventType - Event type: 'alert' | 'camera_status' | 'risk_update' | 'system_status'
   * @param {function} handler - Callback receiving the parsed event object
   * @returns {function} Unsubscribe function
   */
  on(eventType, handler) {
    if (!this._handlers.has(eventType)) {
      this._handlers.set(eventType, new Set());
      this._listenerCounts[eventType] = 0;
    }
    this._handlers.get(eventType).add(handler);
    this._listenerCounts[eventType] = (this._listenerCounts[eventType] || 0) + 1;

    // Return an unsubscribe function
    return () => this.off(eventType, handler);
  }

  /**
   * Remove an event handler.
   *
   * @param {string} eventType
   * @param {function} handler
   */
  off(eventType, handler) {
    const handlers = this._handlers.get(eventType);
    if (handlers) {
      handlers.delete(handler);
      this._listenerCounts[eventType] = Math.max(0, (this._listenerCounts[eventType] || 0) - 1);
      if (handlers.size === 0) {
        this._handlers.delete(eventType);
      }
    }
  }

  /**
   * Remove all handlers for an event type, or all handlers if no type given.
   *
   * @param {string} [eventType]
   */
  offAll(eventType) {
    if (eventType) {
      this._handlers.delete(eventType);
      this._listenerCounts[eventType] = 0;
    } else {
      this._handlers.clear();
      this._listenerCounts = {};
    }
  }

  /** Current connection state. */
  get connectionState() {
    return this._connectionState;
  }

  /** Whether the WebSocket is currently connected. */
  get isConnected() {
    return this._ws !== null &&
      this._ws.readyState === WebSocket.OPEN &&
      this._connectionState === 'CONNECTED';
  }

  /** Number of currently connected clients (always 1 for a single-connection service). */
  get clientCount() {
    return this.isConnected ? 1 : 0;
  }

  // ── Internal ─────────────────────────────────────────────────

  _setState(state) {
    if (this._connectionState === state) return;
    this._connectionState = state;
    // Notify state-change listeners
    const handlers = this._handlers.get('_stateChange');
    if (handlers) {
      handlers.forEach((cb) => {
        try { cb(state); } catch (e) { console.error('[WebSocket] _stateChange handler error:', e); }
      });
    }
  }

  _handleOpen() {
    this._connecting = false;
    this._reconnectDelay = INITIAL_RECONNECT_DELAY_MS;
    this._setState('CONNECTED');
    console.log('[WebSocket] Connected to', WS_URL);
  }

  _handleMessage(event) {
    let data;
    try {
      data = JSON.parse(event.data);
    } catch (err) {
      console.warn('[WebSocket] Failed to parse message:', event.data, err);
      return;
    }

    const type = data.type;
    if (!type) {
      console.warn('[WebSocket] Message missing type field:', data);
      return;
    }

    // Distribute to registered handlers
    const handlers = this._handlers.get(type);
    if (handlers) {
      handlers.forEach((cb) => {
        try { cb(data); } catch (e) { console.error('[WebSocket] Handler error:', e); }
      });
    }
  }

  _handleClose(event) {
    this._ws = null;
    this._connecting = false;

    // Normal close (code 1000) = intentional disconnect; don't auto-reconnect
    if (event.code === 1000) {
      this._setState('DISCONNECTED');
      this._reconnectDelay = INITIAL_RECONNECT_DELAY_MS;
      return;
    }

    this._setState('DISCONNECTED');
    this._scheduleReconnect();
  }

  _handleError(_event) {
    console.warn('[WebSocket] Error event received');
    // Error always leads to close, which handles reconnection
    this._setState('ERROR');
    this._connecting = false;
  }

  _scheduleReconnect() {
    if (this._reconnectTimer !== null) return; // already scheduled
    if (this._ws && this._ws.readyState === WebSocket.OPEN) return; // already connected

    // Show RECONNECTING while waiting to retry
    this._setState('RECONNECTING');

    const delay = Math.min(
      this._reconnectDelay + Math.random() * 1000, // add jitter
      MAX_RECONNECT_DELAY_MS
    );
    this._reconnectDelay = Math.min(
      Math.round(this._reconnectDelay * RECONNECT_MULTIPLIER),
      MAX_RECONNECT_DELAY_MS
    );

    console.log(`[WebSocket] Reconnecting in ${Math.round(delay)}ms (delay=${Math.round(this._reconnectDelay)}ms)`);
    this._reconnectTimer = setTimeout(() => {
      this._reconnectTimer = null;
      this.connect();
    }, delay);
  }

  _clearReconnect() {
    if (this._reconnectTimer !== null) {
      clearTimeout(this._reconnectTimer);
      this._reconnectTimer = null;
    }
  }
}

/** Singleton instance */
export const wsService = new WebSocketService();

/**
 * React hook for WebSocket connection.
 *
 * Returns current connection state and a map of recent events by type.
 * Components using this hook will re-render when the connection state changes
 * or when any event arrives.
 *
 * Usage:
 *   const { connectionState, events } = useWebSocket();
 *
 * @param {string[]} [eventTypes] - Event types to subscribe to (default: all known types)
 * @returns {{ connectionState: ConnectionState, events: Map<string, object[]> }}
 */
export function useWebSocket(eventTypes = ['alert', 'camera_status', 'risk_update', 'system_status']) {
  const [connectionState, setConnectionState] = useState(wsService.connectionState);
  const [events, setEvents] = useState(() => {
    const m = new Map();
    eventTypes.forEach((t) => m.set(t, []));
    return m;
  });

  // Store handlers by event type so they can be removed on cleanup
  const handlerRefs = useRef(new Map());

  // Stable callback to update state when connection state changes
  const handleStateChange = useCallback((state) => {
    setConnectionState(state);
  }, []);

  useEffect(() => {
    // Register state-change handler
    wsService.on('_stateChange', handleStateChange);

    // Register event handlers for each type
    const newHandlerRefs = new Map();
    eventTypes.forEach((type) => {
      const handler = (data) => {
        setEvents((prev) => {
          const next = new Map(prev);
          const existing = next.get(type) || [];
          // Keep last 20 events per type
          next.set(type, [data, ...existing].slice(0, 20));
          return next;
        });
      };
      newHandlerRefs.set(type, handler);
      wsService.on(type, handler);
    });

    handlerRefs.current = newHandlerRefs;

    // Auto-connect on first use
    wsService.connect();

    return () => {
      wsService.off('_stateChange', handleStateChange);
      eventTypes.forEach((type) => {
        const handler = newHandlerRefs.get(type);
        if (handler) wsService.off(type, handler);
      });
    };
  }, [eventTypes.join(','), handleStateChange]); // eslint-disable-line react-hooks/exhaustive-deps

  return { connectionState, events, wsService };
}

/**
 * Hook to subscribe to only the latest alert events.
 * Useful for RecentAlerts to get instant UI updates.
 *
 * @returns {{ connectionState, latestAlerts, addAlert: function }}
 */
export function useLatestAlerts(initialAlerts = []) {
  const { connectionState, events } = useWebSocket(['alert']);
  const [alerts, setAlerts] = useState(initialAlerts);

  // When WebSocket alerts come in, prepend them to the list
  const wsAlerts = events.get('alert') || [];

  useEffect(() => {
    if (wsAlerts.length === 0) return;
    const latest = wsAlerts[0]; // most recent is first in the array
    if (!latest || !latest.alert) return;

    setAlerts((prev) => {
      // Deduplicate by id
      if (prev.some((a) => a.id === latest.alert.id)) return prev;
      return [latest.alert, ...prev].slice(0, 20);
    });
  }, [wsAlerts, connectionState]);

  const addAlert = useCallback((alert) => {
    setAlerts((prev) => {
      if (prev.some((a) => a.id === alert.id)) return prev;
      return [alert, ...prev].slice(0, 20);
    });
  }, []);

  return { connectionState, latestAlerts: alerts, addAlert };
}

export default wsService;
