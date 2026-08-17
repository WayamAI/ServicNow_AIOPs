import { useState } from 'react';
import { Plus } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Skeleton } from '@/components/ui/skeleton';
import { useSession } from '@/context/SessionContext';
import { useIncidentsQuery } from '@/hooks/useIncidents';
import IncidentTable from '@/components/incidents/IncidentTable';
import CreateIncidentDialog from '@/components/incidents/CreateIncidentDialog';
import type { IncidentSeverity, IncidentStatus } from '@/types/api';

export default function Incidents() {
  const { sessionId } = useSession();
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [severityFilter, setSeverityFilter] = useState<string>('all');
  const [dialogOpen, setDialogOpen] = useState(false);

  const { data: incidents, isLoading } = useIncidentsQuery(
    sessionId ?? '',
    statusFilter !== 'all' ? statusFilter : undefined
  );

  const filtered = incidents?.filter((i) =>
    severityFilter === 'all' || i.severity === (severityFilter as IncidentSeverity)
  ) ?? [];

  return (
    <div className="p-6 space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Incidents</h1>
        <Button onClick={() => setDialogOpen(true)} disabled={!sessionId}>
          <Plus className="h-4 w-4 mr-2" />
          Create Incident
        </Button>
      </div>

      <div className="flex gap-3">
        <Select value={statusFilter} onValueChange={(v) => setStatusFilter(v ?? 'all')}>
          <SelectTrigger className="w-40">
            <SelectValue placeholder="Status" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Statuses</SelectItem>
            {(['new', 'rca', 'planned', 'executing', 'validating', 'resolved', 'failed', 'cancelled'] as IncidentStatus[]).map(
              (s) => (
                <SelectItem key={s} value={s}>
                  {s}
                </SelectItem>
              )
            )}
          </SelectContent>
        </Select>

        <Select value={severityFilter} onValueChange={(v) => setSeverityFilter(v ?? 'all')}>
          <SelectTrigger className="w-40">
            <SelectValue placeholder="Severity" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Severities</SelectItem>
            {(['low', 'medium', 'high', 'critical'] as IncidentSeverity[]).map((s) => (
              <SelectItem key={s} value={s}>
                {s}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <Card>
        <CardContent className="p-0">
          {isLoading ? (
            <div className="p-4 space-y-2">
              {[...Array(5)].map((_, i) => (
                <Skeleton key={i} className="h-10 w-full" />
              ))}
            </div>
          ) : (
            <IncidentTable incidents={filtered} />
          )}
        </CardContent>
      </Card>

      {sessionId && (
        <CreateIncidentDialog
          sessionId={sessionId}
          open={dialogOpen}
          onOpenChange={setDialogOpen}
        />
      )}
    </div>
  );
}
