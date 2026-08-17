import { CheckCircle, XCircle, Loader } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { IncidentStatus } from '@/types/api';

const STEPS: { key: IncidentStatus; label: string }[] = [
  { key: 'rca', label: 'RCA' },
  { key: 'planned', label: 'Plan' },
  { key: 'executing', label: 'Execute' },
  { key: 'validating', label: 'Validate' },
];

const STEP_ORDER: IncidentStatus[] = ['new', 'rca', 'planned', 'executing', 'validating', 'resolved'];

function getStepState(stepKey: IncidentStatus, currentStatus: IncidentStatus) {
  if (currentStatus === 'failed' || currentStatus === 'cancelled') {
    const currentIdx = STEP_ORDER.indexOf(currentStatus);
    const stepIdx = STEP_ORDER.indexOf(stepKey);
    if (stepIdx < currentIdx) return 'done';
    return 'pending';
  }

  const currentIdx = STEP_ORDER.indexOf(currentStatus);
  const stepIdx = STEP_ORDER.indexOf(stepKey);

  if (stepIdx < currentIdx) return 'done';
  if (stepIdx === currentIdx) return 'active';
  if (currentStatus === 'resolved') return 'done';
  return 'pending';
}

interface Props {
  status: IncidentStatus;
}

export default function PipelineStepper({ status }: Props) {
  const failed = status === 'failed' || status === 'cancelled';

  return (
    <div className="flex items-center gap-0">
      {STEPS.map((step, i) => {
        const state = getStepState(step.key, status);

        return (
          <div key={step.key} className="flex items-center">
            <div className="flex flex-col items-center gap-1">
              <div
                className={cn(
                  'flex h-8 w-8 items-center justify-center rounded-full border-2 transition-colors',
                  state === 'done' && !failed && 'border-green-500 bg-green-500/20 text-green-400',
                  state === 'active' && 'border-blue-500 bg-blue-500/20 text-blue-400',
                  state === 'pending' && 'border-muted bg-muted/30 text-muted-foreground',
                  failed && state === 'active' && 'border-red-500 bg-red-500/20 text-red-400',
                )}
              >
                {state === 'done' && !failed ? (
                  <CheckCircle className="h-4 w-4" />
                ) : state === 'active' && failed ? (
                  <XCircle className="h-4 w-4" />
                ) : state === 'active' ? (
                  <Loader className="h-4 w-4 animate-spin" />
                ) : (
                  <span className="text-xs font-bold">{i + 1}</span>
                )}
              </div>
              <span
                className={cn(
                  'text-xs font-medium',
                  state === 'done' && !failed && 'text-green-400',
                  state === 'active' && !failed && 'text-blue-400',
                  state === 'active' && failed && 'text-red-400',
                  state === 'pending' && 'text-muted-foreground',
                )}
              >
                {step.label}
              </span>
            </div>
            {i < STEPS.length - 1 && (
              <div
                className={cn(
                  'h-0.5 w-12 mx-1 mb-4',
                  getStepState(STEPS[i + 1].key, status) !== 'pending' || status === 'resolved'
                    ? 'bg-green-500/50'
                    : 'bg-muted'
                )}
              />
            )}
          </div>
        );
      })}
    </div>
  );
}
