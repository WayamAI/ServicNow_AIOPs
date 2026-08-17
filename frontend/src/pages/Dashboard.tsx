import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { AlertTriangle, CheckCircle, XCircle, Activity, Plus } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { useSession } from '@/context/SessionContext';
import { useIncidentsQuery } from '@/hooks/useIncidents';
import { useMonitorStatusQuery } from '@/hooks/useMonitor';
import CreateIncidentDialog from '@/components/incidents/CreateIncidentDialog';
import type { IncidentResponse, IncidentStatus, IncidentSeverity } from '@/types/api';

function statusColor(status: IncidentStatus) {
  switch (status) {
    case 'resolved': return 'bg-green-500/20 text-green-400 border-green-500/30';
    case 'failed':
    case 'cancelled': return 'bg-red-500/20 text-red-400 border-red-500/30';
    case 'new': return 'bg-slate-500/20 text-slate-400 border-slate-500/30';
    default: return 'bg-blue-500/20 text-blue-400 border-blue-500/30';
  }
}

function severityColor(severity: IncidentSeverity) {
  switch (severity) {
    case 'critical': return 'bg-red-500/20 text-red-400 border-red-500/30';
    case 'high': return 'bg-orange-500/20 text-orange-400 border-orange-500/30';
    case 'medium': return 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30';
    case 'low': return 'bg-green-500/20 text-green-400 border-green-500/30';
  }
}

function IncidentRow({ incident }: { incident: IncidentResponse }) {
  const navigate = useNavigate();
  return (
    <div
      className="flex items-center gap-3 py-2 px-3 rounded-md hover:bg-muted/50 cursor-pointer transition-colors"
      onClick={() => navigate(`/incidents/${incident.id}`)}
    >
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium truncate">{incident.title}</p>
        <p className="text-xs text-muted-foreground">
          {incident.container_name ?? 'No container'} •{' '}
          {new Date(incident.created_at).toLocaleString()}
        </p>
      </div>
      <Badge variant="outline" className={`text-xs shrink-0 ${severityColor(incident.severity)}`}>
        {incident.severity}
      </Badge>
      <Badge variant="outline" className={`text-xs shrink-0 ${statusColor(incident.status)}`}>
        {incident.status}
      </Badge>
    </div>
  );
}

export default function Dashboard() {
  const { sessionId, isLoading: sessionLoading } = useSession();
  const [dialogOpen, setDialogOpen] = useState(false);

  const { data: incidents, isLoading: incLoading } = useIncidentsQuery(sessionId ?? '', undefined);
  const { data: monitorStatus } = useMonitorStatusQuery();

  const total = incidents?.length ?? 0;
  const active = incidents?.filter((i) =>
    ['rca', 'planned', 'executing', 'validating'].includes(i.status)
  ).length ?? 0;
  const resolved = incidents?.filter((i) => i.status === 'resolved').length ?? 0;
  const failed = incidents?.filter((i) => i.status === 'failed').length ?? 0;

  const recent = [...(incidents ?? [])].sort(
    (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
  ).slice(0, 10);

  const loading = sessionLoading || incLoading;

  const summaryCards = [
    { title: 'Total', value: total, icon: Activity, color: 'text-blue-400' },
    { title: 'Active', value: active, icon: AlertTriangle, color: 'text-yellow-400' },
    { title: 'Resolved', value: resolved, icon: CheckCircle, color: 'text-green-400' },
    { title: 'Failed', value: failed, icon: XCircle, color: 'text-red-400' },
  ];

  return (
    <div className="p-4 sm:p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Dashboard</h1>
        <Button
          onClick={() => setDialogOpen(true)}
          disabled={!sessionId}
        >
          <Plus className="h-4 w-4 mr-2" />
          Create Incident
        </Button>
      </div>

      {/* Summary cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {summaryCards.map(({ title, value, icon: Icon, color }) => (
          <Card key={title}>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">{title}</CardTitle>
              <Icon className={`h-4 w-4 ${color}`} />
            </CardHeader>
            <CardContent>
              {loading ? (
                <Skeleton className="h-8 w-16" />
              ) : (
                <p className="text-3xl font-bold">{value}</p>
              )}
            </CardContent>
          </Card>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Recent incidents */}
        <div className="lg:col-span-2">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Recent Incidents</CardTitle>
            </CardHeader>
            <CardContent>
              {loading ? (
                <div className="space-y-2">
                  {[...Array(3)].map((_, i) => (
                    <Skeleton key={i} className="h-10 w-full" />
                  ))}
                </div>
              ) : recent.length === 0 ? (
                <p className="text-sm text-muted-foreground py-4 text-center">
                  No incidents yet. Create one to get started.
                </p>
              ) : (
                <div className="space-y-1">
                  {recent.map((incident) => (
                    <IncidentRow key={incident.id} incident={incident} />
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Monitor status */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Monitor Status</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex items-center gap-2">
              <span
                className={`h-2.5 w-2.5 rounded-full shrink-0 ${
                  monitorStatus?.status === 'running'
                    ? 'bg-green-500'
                    : 'bg-muted-foreground/40'
                }`}
              />
              <span className="text-sm capitalize">{monitorStatus?.status ?? 'Unknown'}</span>
            </div>
            <div className="text-sm space-y-1">
              <div className="flex justify-between">
                <span className="text-muted-foreground">Containers</span>
                <span>{monitorStatus?.monitored_containers ?? 0}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Active Incidents</span>
                <span>{monitorStatus?.active_incidents ?? 0}</span>
              </div>
              {monitorStatus?.last_check && (
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Last Check</span>
                  <span className="text-xs">
                    {new Date(monitorStatus.last_check).toLocaleTimeString()}
                  </span>
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      </div>

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
