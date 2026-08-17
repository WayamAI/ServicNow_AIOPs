import { useSSEContext } from '@/context/SSEContext';
import { useIncidentsQuery } from '@/hooks/useIncidents';
import { useSession } from '@/context/SessionContext';

export default function StatusBar() {
  const { connectionStatus } = useSSEContext();
  const { sessionId } = useSession();
  const { data: incidents } = useIncidentsQuery(sessionId ?? '');

  const activeCount = incidents?.filter((i) =>
    ['rca', 'planned', 'executing', 'validating'].includes(i.status)
  ).length ?? 0;

  const dotColor =
    connectionStatus === 'connected'
      ? 'bg-green-500'
      : connectionStatus === 'connecting'
      ? 'bg-yellow-500 animate-pulse'
      : 'bg-muted-foreground/40';

  const statusText =
    connectionStatus === 'connected'
      ? 'Connected'
      : connectionStatus === 'connecting'
      ? 'Connecting...'
      : 'Disconnected';

  return (
    <footer className="border-t bg-card px-4 py-2 flex items-center gap-4 text-xs text-muted-foreground shrink-0">
      <div className="flex items-center gap-1.5">
        <span className={`h-2 w-2 rounded-full shrink-0 ${dotColor}`} />
        <span>{statusText}</span>
      </div>
      <span>•</span>
      <span>{activeCount} active incident{activeCount !== 1 ? 's' : ''}</span>
    </footer>
  );
}
