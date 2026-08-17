import { createContext, useContext, useEffect, useState } from 'react';
import type { ReactNode } from 'react';
import { createSession, getSessions } from '@/api/client';

interface SessionContextValue {
  sessionId: string | null;
  isLoading: boolean;
}

const SessionContext = createContext<SessionContextValue>({
  sessionId: null,
  isLoading: true,
});

export function SessionProvider({ children }: { children: ReactNode }) {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    async function bootstrap() {
      try {
        const sessions = await getSessions();
        const active = sessions.find((s) => s.status === 'active');
        if (active) {
          setSessionId(active.id);
        } else {
          const created = await createSession();
          setSessionId(created.id);
        }
      } catch {
        // backend may be offline
      } finally {
        setIsLoading(false);
      }
    }
    void bootstrap();
  }, []);

  return (
    <SessionContext.Provider value={{ sessionId, isLoading }}>
      {children}
    </SessionContext.Provider>
  );
}

export function useSession() {
  return useContext(SessionContext);
}
