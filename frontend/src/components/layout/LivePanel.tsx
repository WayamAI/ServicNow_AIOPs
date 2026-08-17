import { useEffect, useRef, useState } from 'react';
import { ChevronRight, ChevronLeft, Trash2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import { useSSEContext } from '@/context/SSEContext';
import type { SSEEvent } from '@/types/api';
import { cn } from '@/lib/utils';

const EVENT_COLORS: Record<string, string> = {
  agent_start: 'text-blue-400',
  tool_call: 'text-yellow-400',
  tool_result: 'text-green-400',
  agent_response: 'text-purple-400',
  error: 'text-red-400',
};

const EVENT_ICONS: Record<string, string> = {
  agent_start: '▶',
  tool_call: '⚙',
  tool_result: '✓',
  agent_response: '◆',
  error: '✗',
};

function EventItem({ event }: { event: SSEEvent }) {
  const color = EVENT_COLORS[event.event_type] ?? 'text-muted-foreground';
  const icon = EVENT_ICONS[event.event_type] ?? '•';
  const dataPreview = Object.keys(event.data).slice(0, 2).map(k => `${k}: ...`).join(', ');

  return (
    <div className="border-b border-border/40 px-3 py-2 space-y-0.5">
      <div className="flex items-center gap-1.5">
        <span className={cn('text-xs font-mono shrink-0', color)}>{icon}</span>
        <span className={cn('text-xs font-medium', color)}>{event.event_type}</span>
        {event.agent_name && (
          <span className="text-xs text-muted-foreground truncate">
            {event.agent_name}
          </span>
        )}
        <span className="ml-auto text-xs text-muted-foreground shrink-0">
          {new Date(event.timestamp).toLocaleTimeString()}
        </span>
      </div>
      {dataPreview && (
        <p className="text-xs text-muted-foreground/70 truncate pl-4">{dataPreview}</p>
      )}
    </div>
  );
}

export default function LivePanel() {
  const [collapsed, setCollapsed] = useState(false);
  const { events, clearEvents } = useSSEContext();
  const scrollAreaRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const viewport = scrollAreaRef.current?.querySelector<HTMLDivElement>(
      '[data-slot="scroll-area-viewport"]'
    );
    if (viewport) {
      viewport.scrollTop = viewport.scrollHeight;
    }
  }, [events]);

  if (collapsed) {
    return (
      <div className="flex flex-col items-center border-l bg-card py-4 w-10 shrink-0">
        <Button
          variant="ghost"
          size="icon"
          className="h-6 w-6"
          onClick={() => setCollapsed(false)}
        >
          <ChevronLeft className="h-3 w-3" />
        </Button>
        <span
          className="text-xs text-muted-foreground mt-4"
          style={{ writingMode: 'vertical-rl', transform: 'rotate(180deg)' }}
        >
          Live Events
        </span>
      </div>
    );
  }

  return (
    <div className="flex flex-col border-l bg-card w-80 shrink-0 min-h-0 h-full">
      <div className="flex items-center justify-between p-3 border-b">
        <div className="flex items-center gap-2">
          <h3 className="text-sm font-medium">Live Events</h3>
          {events.length > 0 && (
            <span className="text-xs text-muted-foreground">({events.length})</span>
          )}
        </div>
        <div className="flex items-center gap-1">
          {events.length > 0 && (
            <Button
              variant="ghost"
              size="icon"
              className="h-6 w-6"
              onClick={clearEvents}
              title="Clear events"
            >
              <Trash2 className="h-3 w-3" />
            </Button>
          )}
          <Button
            variant="ghost"
            size="icon"
            className="h-6 w-6"
            onClick={() => setCollapsed(true)}
          >
            <ChevronRight className="h-3 w-3" />
          </Button>
        </div>
      </div>
      <div ref={scrollAreaRef} className="flex-1 min-h-0">
        <ScrollArea className="h-full">
          {events.length === 0 ? (
            <div className="p-3 text-xs text-muted-foreground">
              Waiting for SSE events...
            </div>
          ) : (
            <div>
              {events.map((event, i) => (
                <EventItem key={`${event.timestamp}-${i}`} event={event} />
              ))}
            </div>
          )}
        </ScrollArea>
      </div>
    </div>
  );
}
