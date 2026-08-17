import { useState } from 'react';
import { Plus } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { useMonitorContainersQuery, useMonitorStatusQuery } from '@/hooks/useMonitor';
import ContainerTable from '@/components/monitor/ContainerTable';
import AddContainerForm from '@/components/monitor/AddContainerForm';

export default function Monitor() {
  const [addOpen, setAddOpen] = useState(false);
  const { data: containers, isLoading: containersLoading } = useMonitorContainersQuery();
  const { data: status } = useMonitorStatusQuery();

  return (
    <div className="p-4 sm:p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Monitor</h1>
        <Button onClick={() => setAddOpen(true)}>
          <Plus className="h-4 w-4 mr-2" />
          Add Container
        </Button>
      </div>

      {/* Status card */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Status</CardTitle>
          </CardHeader>
          <CardContent className="flex items-center gap-2">
            <span
              className={`h-2.5 w-2.5 rounded-full shrink-0 ${
                status?.status === 'running' ? 'bg-green-500' : 'bg-muted-foreground/40'
              }`}
            />
            <span className="capitalize text-sm">{status?.status ?? '—'}</span>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Containers</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold">{status?.monitored_containers ?? '—'}</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Active Incidents</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold">{status?.active_incidents ?? '—'}</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Last Check</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">
              {status?.last_check
                ? new Date(status.last_check).toLocaleTimeString()
                : '—'}
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Containers table */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Monitored Containers</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          {containersLoading ? (
            <div className="p-4 space-y-2">
              {[...Array(3)].map((_, i) => (
                <Skeleton key={i} className="h-10 w-full" />
              ))}
            </div>
          ) : (
            <ContainerTable containers={containers ?? []} />
          )}
        </CardContent>
      </Card>

      <AddContainerForm open={addOpen} onOpenChange={setAddOpen} />
    </div>
  );
}
