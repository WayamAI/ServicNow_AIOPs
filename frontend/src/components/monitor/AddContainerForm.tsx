import { useState } from 'react';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { useAddContainerMutation } from '@/hooks/useMonitor';

interface Props {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export default function AddContainerForm({ open, onOpenChange }: Props) {
  const [containerName, setContainerName] = useState('');
  const [image, setImage] = useState('');
  const [expectedStatus, setExpectedStatus] = useState('running');

  const mutation = useAddContainerMutation();

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    await mutation.mutateAsync({
      container_name: containerName.trim(),
      image: image.trim(),
      expected_status: expectedStatus.trim(),
    });
    onOpenChange(false);
    setContainerName('');
    setImage('');
    setExpectedStatus('running');
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Add Container to Monitor</DialogTitle>
        </DialogHeader>
        <form onSubmit={(e) => { void handleSubmit(e); }} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="container-name">Container Name *</Label>
            <Input
              id="container-name"
              value={containerName}
              onChange={(e) => setContainerName(e.target.value)}
              placeholder="e.g. my-service"
              required
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="image">Image</Label>
            <Input
              id="image"
              value={image}
              onChange={(e) => setImage(e.target.value)}
              placeholder="e.g. nginx:latest"
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="expected-status">Expected Status</Label>
            <Input
              id="expected-status"
              value={expectedStatus}
              onChange={(e) => setExpectedStatus(e.target.value)}
              placeholder="running"
            />
          </div>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={mutation.isPending}>
              {mutation.isPending ? 'Adding...' : 'Add Container'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
