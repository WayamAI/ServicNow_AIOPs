import { useNavigate } from 'react-router-dom';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import type { IncidentResponse, IncidentStatus, IncidentSeverity } from '@/types/api';

function statusVariant(status: IncidentStatus): string {
  switch (status) {
    case 'resolved': return 'bg-green-500/20 text-green-400 border-green-500/30';
    case 'failed':
    case 'cancelled': return 'bg-red-500/20 text-red-400 border-red-500/30';
    case 'new': return 'bg-slate-500/20 text-slate-400 border-slate-500/30';
    default: return 'bg-blue-500/20 text-blue-400 border-blue-500/30';
  }
}

function severityVariant(severity: IncidentSeverity): string {
  switch (severity) {
    case 'critical': return 'bg-red-500/20 text-red-400 border-red-500/30';
    case 'high': return 'bg-orange-500/20 text-orange-400 border-orange-500/30';
    case 'medium': return 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30';
    case 'low': return 'bg-green-500/20 text-green-400 border-green-500/30';
  }
}

function duration(createdAt: string, resolvedAt: string | null): string {
  const end = resolvedAt ? new Date(resolvedAt) : new Date();
  const ms = end.getTime() - new Date(createdAt).getTime();
  const minutes = Math.floor(ms / 60_000);
  if (minutes < 60) return `${minutes}m`;
  const hours = Math.floor(minutes / 60);
  return `${hours}h ${minutes % 60}m`;
}

interface Props {
  incidents: IncidentResponse[];
}

export default function IncidentTable({ incidents }: Props) {
  const navigate = useNavigate();

  if (incidents.length === 0) {
    return (
      <div className="text-center py-12 text-muted-foreground text-sm">
        No incidents found.
      </div>
    );
  }

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Title</TableHead>
          <TableHead>Container</TableHead>
          <TableHead>Status</TableHead>
          <TableHead>Severity</TableHead>
          <TableHead>Created</TableHead>
          <TableHead>Duration</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {incidents.map((incident) => (
          <TableRow
            key={incident.id}
            className="cursor-pointer hover:bg-muted/50"
            onClick={() => navigate(`/incidents/${incident.id}`)}
          >
            <TableCell className="font-medium max-w-xs truncate">{incident.title}</TableCell>
            <TableCell className="text-muted-foreground">
              {incident.container_name ?? '—'}
            </TableCell>
            <TableCell>
              <Badge variant="outline" className={`text-xs ${statusVariant(incident.status)}`}>
                {incident.status}
              </Badge>
            </TableCell>
            <TableCell>
              <Badge variant="outline" className={`text-xs ${severityVariant(incident.severity)}`}>
                {incident.severity}
              </Badge>
            </TableCell>
            <TableCell className="text-muted-foreground text-sm">
              {new Date(incident.created_at).toLocaleString()}
            </TableCell>
            <TableCell className="text-muted-foreground text-sm">
              {duration(incident.created_at, incident.resolved_at)}
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
