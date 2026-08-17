import { useState } from 'react';
import { Trash2 } from 'lucide-react';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
  DialogDescription,
} from '@/components/ui/dialog';
import { Badge } from '@/components/ui/badge';
import { useRemoveContainerMutation } from '@/hooks/useMonitor';
import type { MonitorContainerResponse } from '@/types/api';

interface Props {
  containers: MonitorContainerResponse[];
}

export default function ContainerTable({ containers }: Props) {
  const [confirmName, setConfirmName] = useState<string | null>(null);
  const removeMutation = useRemoveContainerMutation();

  async function handleRemove() {
    if (!confirmName) return;
    await removeMutation.mutateAsync(confirmName);
    setConfirmName(null);
  }

  if (containers.length === 0) {
    return (
      <div className="text-center py-12 text-muted-foreground text-sm">
        No containers being monitored.
      </div>
    );
  }

  return (
    <>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Container Name</TableHead>
            <TableHead>Image</TableHead>
            <TableHead>Expected Status</TableHead>
            <TableHead className="w-16"></TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {containers.map((c) => (
            <TableRow key={c.container_name}>
              <TableCell className="font-medium">{c.container_name}</TableCell>
              <TableCell className="text-muted-foreground">{c.image || '—'}</TableCell>
              <TableCell>
                <Badge variant="outline" className="text-xs">{c.expected_status}</Badge>
              </TableCell>
              <TableCell>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-7 w-7 text-destructive hover:text-destructive"
                  onClick={() => setConfirmName(c.container_name)}
                >
                  <Trash2 className="h-4 w-4" />
                </Button>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>

      <Dialog open={!!confirmName} onOpenChange={(open) => !open && setConfirmName(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Remove Container?</DialogTitle>
            <DialogDescription>
              Stop monitoring <strong>{confirmName}</strong>? This cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setConfirmName(null)}>
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={() => { void handleRemove(); }}
              disabled={removeMutation.isPending}
            >
              {removeMutation.isPending ? 'Removing...' : 'Remove'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
