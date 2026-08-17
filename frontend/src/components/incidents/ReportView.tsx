import { Sheet, SheetContent, SheetHeader, SheetTitle } from '@/components/ui/sheet';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Skeleton } from '@/components/ui/skeleton';
import { useIncidentReportQuery } from '@/hooks/useIncidents';

interface Props {
  incidentId: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export default function ReportView({ incidentId, open, onOpenChange }: Props) {
  const { data, isLoading } = useIncidentReportQuery(open ? incidentId : '');

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent className="w-full sm:max-w-2xl">
        <SheetHeader>
          <SheetTitle>Incident Report</SheetTitle>
        </SheetHeader>
        <ScrollArea className="h-full mt-4 pr-4">
          {isLoading ? (
            <div className="space-y-2">
              {[...Array(8)].map((_, i) => (
                <Skeleton key={i} className="h-4 w-full" />
              ))}
            </div>
          ) : (
            <pre className="text-sm whitespace-pre-wrap font-mono leading-relaxed">
              {data?.report ?? 'No report available.'}
            </pre>
          )}
        </ScrollArea>
      </SheetContent>
    </Sheet>
  );
}
