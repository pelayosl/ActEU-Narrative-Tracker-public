"use client";

import { TopicCard } from "./topic-card";
import { MergeDialog } from "./merge-dialog";
import { Button } from "@/components/ui/button";
import { usePipelineStore } from "@/stores/pipeline-store";

// TODO: handle sub-states (generating, generated, reconciling, reconciled) via topicSubStep.
// 2b: list raw topics with edit/delete/checkbox-select, "Merge Selected", "Reconcile Topics", "Skip to Labelling".
// 2c: reconciled topics with edit/delete (delete = split back), "Accept Topics", "Cancel".
export function StepTopicModelling() {
  const generated = usePipelineStore((s) => s.generatedTopics);
  const reconciled = usePipelineStore((s) => s.reconciledTopics);
  const subStep = usePipelineStore((s) => s.topicSubStep);
  const setStep = usePipelineStore((s) => s.setStep);

  if (subStep === "generating" || subStep === "reconciling") {
    return (
      <div className="space-y-3">
        <div className="h-2 w-full overflow-hidden rounded-full bg-bg">
          <div className="h-full w-1/3 animate-pulseRed bg-acteu-red" />
        </div>
        <p className="text-sm text-muted-foreground">
          {subStep === "generating" ? "Running BERTopic… this may take a few minutes." : "Reconciling topics with LLM…"}
        </p>
      </div>
    );
  }

  const topics = subStep === "reconciled" ? reconciled : generated;

  return (
    <div className="space-y-4">
      <ul className="space-y-2">
        {topics.map((t) => (
          <TopicCard key={t.topic_id} topic={t} reconciled={subStep === "reconciled"} />
        ))}
      </ul>
      <div className="flex gap-2">
        {subStep === "reconciled" ? (
          <>
            <Button onClick={() => setStep("label")}>Accept Topics</Button>
            <Button variant="ghost">Cancel</Button>
          </>
        ) : (
          <>
            <Button>Reconcile Topics</Button>
            <Button variant="outline" onClick={() => setStep("label")}>Skip to Labelling →</Button>
          </>
        )}
      </div>
      <MergeDialog />
    </div>
  );
}
