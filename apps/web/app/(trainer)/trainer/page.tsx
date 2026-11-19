import { Card, EmptyState, PageHeader } from "@/components/ui/primitives";

export default function TrainerQueue() {
  return (
    <>
      <PageHeader
        eyebrow="Trainer workspace"
        title="Review queue"
        description="Evaluations that need your decision appear here, riskiest first."
      />
      <Card>
        <EmptyState icon="inbox" title="Nothing to review yet">
          When interns hand in work that needs a trainer, it will wait here with the reason it was flagged.
        </EmptyState>
      </Card>
    </>
  );
}
