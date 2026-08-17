import { createContext, useContext, useEffect } from 'react';
import type { ReactNode } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { useSSE, type ConnectionStatus } from '@/hooks/useSSE';
import type { SSEEvent } from '@/types/api';
import { useSession } from './SessionContext';

interface SSEContextValue {
  events: SSEEvent[];
  connectionStatus: ConnectionStatus;
  clearEvents: () => void;
}

const SSEContext = createContext<SSEContextValue>({
  events: [],
  connectionStatus: 'disconnected',
  clearEvents: () => undefined,
});

export function SSEProvider({ children }: { children: ReactNode }) {
  const { sessionId } = useSession();
  const { events, connectionStatus, clearEvents } = useSSE(sessionId);
  const qc = useQueryClient();

  // Invalidate incident queries on agent events
  useEffect(() => {
    const last = events[events.length - 1];
    if (!last) return;

    if (['agent_start', 'agent_response', 'error'].includes(last.event_type)) {
      if (sessionId) {
        void qc.invalidateQueries({ queryKey: ['incidents', sessionId] });
      }
      void qc.invalidateQueries({ queryKey: ['incident'] });
    }
  }, [events, qc, sessionId]);

  return (
    <SSEContext.Provider value={{ events, connectionStatus, clearEvents }}>
      {children}
    </SSEContext.Provider>
  );
}

export function useSSEContext() {
  return useContext(SSEContext);
}
