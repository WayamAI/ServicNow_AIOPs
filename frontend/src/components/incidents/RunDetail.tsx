import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from '@/components/ui/accordion';
import { Badge } from '@/components/ui/badge';
import type { RunResponse } from '@/types/api';

function JsonView({ data }: { data: Record<string, unknown> | null }) {
  if (!data) return <p className="text-muted-foreground text-xs">No data</p>;
  return (
    <pre className="text-xs bg-muted/50 rounded p-3 overflow-auto max-h-64 whitespace-pre-wrap">
      {JSON.stringify(data, null, 2)}
    </pre>
  );
}

interface Props {
  run: RunResponse;
}

export default function RunDetail({ run }: Props) {
  return (
    <Accordion className="w-full">
      <AccordionItem value="rca">
        <AccordionTrigger className="text-sm">RCA Result</AccordionTrigger>
        <AccordionContent>
          <JsonView data={run.rca_result} />
        </AccordionContent>
      </AccordionItem>
      <AccordionItem value="plan">
        <AccordionTrigger className="text-sm">Remediation Plan</AccordionTrigger>
        <AccordionContent>
          <JsonView data={run.plan_result} />
        </AccordionContent>
      </AccordionItem>
      <AccordionItem value="execution">
        <AccordionTrigger className="text-sm">Execution Log</AccordionTrigger>
        <AccordionContent>
          <JsonView data={run.execution_result} />
        </AccordionContent>
      </AccordionItem>
      <AccordionItem value="validation">
        <AccordionTrigger className="text-sm">Validation</AccordionTrigger>
        <AccordionContent>
          <JsonView data={run.validation_result} />
        </AccordionContent>
      </AccordionItem>
      <div className="py-2 text-xs text-muted-foreground flex gap-4">
        <span>Started: {new Date(run.started_at).toLocaleString()}</span>
        {run.completed_at && (
          <span>Completed: {new Date(run.completed_at).toLocaleString()}</span>
        )}
        <Badge variant="outline" className="text-xs">
          {run.status}
        </Badge>
      </div>
    </Accordion>
  );
}
