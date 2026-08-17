import { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, FileText, StopCircle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Skeleton } from '@/components/ui/skeleton';
import { toast } from 'sonner';
import { useIncidentQuery, useCancelRunMutation } from '@/hooks/useIncidents';
import PipelineStepper from '@/components/incidents/PipelineStepper';
import RunDetail from '@/components/incidents/RunDetail';
import ReportView from '@/components/incidents/ReportView';
import type { IncidentStatus, IncidentSeverity } from '@/types/api';

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

export default function IncidentDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [reportOpen, setReportOpen] = useState(false);

  const { data: incident, isLoading } = useIncidentQuery(id ?? '');
  const cancelMutation = useCancelRunMutation();

  const activeRun = incident?.runs.find((r) => r.status === 'running');

  async function handleCancel() {
    if (!activeRun) return;
    try {
      await cancelMutation.mutateAsync(activeRun.id);
      toast.success('Run cancelled');
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to cancel run');
    }
  }

  if (isLoading) {
    return (
      <div className="p-6 space-y-4">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-24 w-full" />
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }

  if (!incident) {
    return (
      <div className="p-6">
        <p className="text-muted-foreground">Incident not found.</p>
        <Button variant="ghost" onClick={() => navigate('/incidents')} className="mt-4">
          <ArrowLeft className="h-4 w-4 mr-2" />
          Back to Incidents
        </Button>
      </div>
    );
  }

  const sortedRuns = [...incident.runs].sort((a, b) => a.run_number - b.run_number);

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-start gap-3">
          <Button variant="ghost" size="icon" onClick={() => navigate('/incidents')} className="mt-1 shrink-0">
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <div>
            <h1 className="text-xl font-semibold">{incident.title}</h1>
            <div className="flex flex-wrap items-center gap-2 mt-1">
              <Badge variant="outline" className={`text-xs ${statusColor(incident.status)}`}>
                {incident.status}
              </Badge>
              <Badge variant="outline" className={`text-xs ${severityColor(incident.severity)}`}>
                {incident.severity}
              </Badge>
              {incident.container_name && (
                <span className="text-xs text-muted-foreground">
                  Container: {incident.container_name}
                </span>
              )}
              <span className="text-xs text-muted-foreground">
                Created: {new Date(incident.created_at).toLocaleString()}
              </span>
            </div>
          </div>
        </div>
        <div className="flex gap-2 shrink-0">
          {incident.status === 'resolved' && (
            <Button variant="outline" size="sm" onClick={() => setReportOpen(true)}>
              <FileText className="h-4 w-4 mr-2" />
              Report
            </Button>
          )}
          {activeRun && (
            <Button
              variant="destructive"
              size="sm"
              onClick={() => { void handleCancel(); }}
              disabled={cancelMutation.isPending}
            >
              <StopCircle className="h-4 w-4 mr-2" />
              Cancel
            </Button>
          )}
        </div>
      </div>

      {/* Description */}
      {incident.description && (
        <p className="text-sm text-muted-foreground">{incident.description}</p>
      )}

      {/* Pipeline stepper */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-medium text-muted-foreground">Pipeline Progress</CardTitle>
        </CardHeader>
        <CardContent>
          <PipelineStepper status={incident.status} />
        </CardContent>
      </Card>

      {/* Runs */}
      {sortedRuns.length > 0 ? (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Run History</CardTitle>
          </CardHeader>
          <CardContent>
            <Tabs defaultValue={`run-${sortedRuns[sortedRuns.length - 1].id}`}>
              <TabsList className="flex-wrap h-auto">
                {sortedRuns.map((run) => (
                  <TabsTrigger key={run.id} value={`run-${run.id}`} className="text-xs">
                    Run {run.run_number}
                    <span
                      className={`ml-1 h-1.5 w-1.5 rounded-full inline-block ${
                        run.status === 'running' ? 'bg-blue-400' :
                        run.status === 'completed' ? 'bg-green-400' :
                        'bg-red-400'
                      }`}
                    />
                  </TabsTrigger>
                ))}
              </TabsList>
              {sortedRuns.map((run) => (
                <TabsContent key={run.id} value={`run-${run.id}`} className="mt-4">
                  <RunDetail run={run} />
                </TabsContent>
              ))}
            </Tabs>
          </CardContent>
        </Card>
      ) : (
        <Card>
          <CardContent className="py-8 text-center text-muted-foreground text-sm">
            No runs yet. Pipeline will start automatically once created.
          </CardContent>
        </Card>
      )}

      <ReportView
        incidentId={incident.id}
        open={reportOpen}
        onOpenChange={setReportOpen}
      />
    </div>
  );
}
