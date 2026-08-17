import { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Separator } from '@/components/ui/separator';
import { Skeleton } from '@/components/ui/skeleton';
import { useConfigQuery, useUpdateConfigMutation } from '@/hooks/useConfig';
import type { ConfigUpdateRequest } from '@/types/api';

interface MutableConfig {
  monitor_poll_interval: string;
  orchestrator_poll_interval: string;
  max_incident_retries: string;
  max_tool_iterations: string;
}

export default function Settings() {
  const { data: config, isLoading } = useConfigQuery();
  const mutation = useUpdateConfigMutation();

  const [form, setForm] = useState<MutableConfig>({
    monitor_poll_interval: '',
    orchestrator_poll_interval: '',
    max_incident_retries: '',
    max_tool_iterations: '',
  });
  const [dirty, setDirty] = useState(false);

  useEffect(() => {
    if (config) {
      setForm({
        monitor_poll_interval: String(config.monitor_poll_interval),
        orchestrator_poll_interval: String(config.orchestrator_poll_interval),
        max_incident_retries: String(config.max_incident_retries),
        max_tool_iterations: String(config.max_tool_iterations),
      });
      setDirty(false);
    }
  }, [config]);

  function handleChange(field: keyof MutableConfig, value: string) {
    setForm((prev) => ({ ...prev, [field]: value }));
    setDirty(true);
  }

  function handleReset() {
    if (config) {
      setForm({
        monitor_poll_interval: String(config.monitor_poll_interval),
        orchestrator_poll_interval: String(config.orchestrator_poll_interval),
        max_incident_retries: String(config.max_incident_retries),
        max_tool_iterations: String(config.max_tool_iterations),
      });
      setDirty(false);
    }
  }

  async function handleSave(e: React.FormEvent) {
    e.preventDefault();
    const body: ConfigUpdateRequest = {
      monitor_poll_interval: Number(form.monitor_poll_interval),
      orchestrator_poll_interval: Number(form.orchestrator_poll_interval),
      max_incident_retries: Number(form.max_incident_retries),
      max_tool_iterations: Number(form.max_tool_iterations),
    };
    await mutation.mutateAsync(body);
    setDirty(false);
  }

  return (
    <div className="p-6 max-w-2xl space-y-6">
      <h1 className="text-2xl font-semibold">Settings</h1>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Runtime Configuration</CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="space-y-4">
              {[...Array(4)].map((_, i) => (
                <Skeleton key={i} className="h-10 w-full" />
              ))}
            </div>
          ) : (
            <form onSubmit={(e) => { void handleSave(e); }} className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="monitor-poll">Monitor Poll Interval (s)</Label>
                  <Input
                    id="monitor-poll"
                    type="number"
                    min={1}
                    value={form.monitor_poll_interval}
                    onChange={(e) => handleChange('monitor_poll_interval', e.target.value)}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="orch-poll">Orchestrator Poll Interval (s)</Label>
                  <Input
                    id="orch-poll"
                    type="number"
                    min={1}
                    value={form.orchestrator_poll_interval}
                    onChange={(e) => handleChange('orchestrator_poll_interval', e.target.value)}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="max-retries">Max Incident Retries</Label>
                  <Input
                    id="max-retries"
                    type="number"
                    min={0}
                    value={form.max_incident_retries}
                    onChange={(e) => handleChange('max_incident_retries', e.target.value)}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="max-tools">Max Tool Iterations</Label>
                  <Input
                    id="max-tools"
                    type="number"
                    min={1}
                    value={form.max_tool_iterations}
                    onChange={(e) => handleChange('max_tool_iterations', e.target.value)}
                  />
                </div>
              </div>

              <div className="flex gap-2 pt-2">
                <Button type="submit" disabled={!dirty || mutation.isPending}>
                  {mutation.isPending ? 'Saving...' : 'Save Changes'}
                </Button>
                <Button
                  type="button"
                  variant="outline"
                  onClick={handleReset}
                  disabled={!dirty}
                >
                  Reset
                </Button>
              </div>
            </form>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Server Information</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {isLoading ? (
            <div className="space-y-2">
              {[...Array(4)].map((_, i) => (
                <Skeleton key={i} className="h-5 w-full" />
              ))}
            </div>
          ) : (
            <>
              <Separator />
              <div className="grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
                <span className="text-muted-foreground">Host</span>
                <span className="font-mono">{config?.host}</span>
                <span className="text-muted-foreground">Port</span>
                <span className="font-mono">{config?.port}</span>
                <span className="text-muted-foreground">Codestral Deployment</span>
                <span className="font-mono truncate">{config?.codestral_deployment}</span>
                <span className="text-muted-foreground">GPT-4o Mini Deployment</span>
                <span className="font-mono truncate">{config?.gpt4o_mini_deployment}</span>
              </div>
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
