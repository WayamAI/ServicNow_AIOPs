import { useCallback, useEffect, useRef, useState } from 'react';
import type { SSEEvent, SSEEventType } from '@/types/api';

export type ConnectionStatus = 'connecting' | 'connected' | 'disconnected';

interface SSEState {
  events: SSEEvent[];
  connectionStatus: ConnectionStatus;
}

const NAMED_EVENT_TYPES: SSEEventType[] = [
  'connected',
  'heartbeat',
  'agent_start',
  'tool_call',
  'tool_result',
  'agent_response',
  'error',
];

const MAX_EVENTS = 500;

export function useSSE(sessionId: string | null) {
  const [state, setState] = useState<SSEState>({
    events: [],
    connectionStatus: 'disconnected',
  });

  const esRef = useRef<EventSource | null>(null);
  const backoffRef = useRef(1000);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const mountedRef = useRef(true);

  const pushEvent = useCallback((event: SSEEvent) => {
    setState((prev) => ({
      ...prev,
      events: [...prev.events.slice(-(MAX_EVENTS - 1)), event],
    }));
  }, []);

  const connect = useCallback(() => {
    if (!sessionId || !mountedRef.current) return;

    setState((prev) => ({ ...prev, connectionStatus: 'connecting' }));

    const url = `/api/sessions/${sessionId}/stream`;
    const es = new EventSource(url);
    esRef.current = es;

    es.onopen = () => {
      if (!mountedRef.current) return;
      backoffRef.current = 1000;
      setState((prev) => ({ ...prev, connectionStatus: 'connected' }));
    };

    // Listen to each named event type individually (NOT onmessage)
    NAMED_EVENT_TYPES.forEach((eventType) => {
      es.addEventListener(eventType, (e: MessageEvent) => {
        if (!mountedRef.current) return;
        if (eventType === 'heartbeat') return; // ignore heartbeats

        if (eventType === 'connected') {
          setState((prev) => ({ ...prev, connectionStatus: 'connected' }));
          return;
        }

        try {
          const parsed = JSON.parse(e.data as string) as SSEEvent;
          pushEvent(parsed);
        } catch {
          // ignore malformed events
        }
      });
    });

    es.onerror = () => {
      if (!mountedRef.current) return;
      es.close();
      esRef.current = null;
      setState((prev) => ({ ...prev, connectionStatus: 'disconnected' }));

      // Exponential backoff reconnect
      const delay = Math.min(backoffRef.current, 30_000);
      backoffRef.current = Math.min(backoffRef.current * 2, 30_000);

      reconnectTimerRef.current = setTimeout(() => {
        if (mountedRef.current) connect();
      }, delay);
    };
  }, [sessionId, pushEvent]);

  useEffect(() => {
    mountedRef.current = true;

    if (sessionId) {
      connect();
    }

    return () => {
      mountedRef.current = false;
      if (reconnectTimerRef.current) {
        clearTimeout(reconnectTimerRef.current);
      }
      if (esRef.current) {
        esRef.current.close();
        esRef.current = null;
      }
    };
  }, [sessionId, connect]);

  const clearEvents = useCallback(() => {
    setState((prev) => ({ ...prev, events: [] }));
  }, []);

  return {
    events: state.events,
    connectionStatus: state.connectionStatus,
    clearEvents,
  };
}
