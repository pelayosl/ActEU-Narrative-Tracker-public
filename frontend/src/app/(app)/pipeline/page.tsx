"use client";

import { Stepper } from "@/components/pipeline/stepper";
import { StepSearch } from "@/components/pipeline/step-search";
import { StepTopicModelling } from "@/components/pipeline/step-topic-modelling";
import { StepLabelDataset } from "@/components/pipeline/step-label-dataset";
import { ProjectSelectorDialog } from "@/components/projects/project-selector-dialog";
import { usePipelineStore } from "@/stores/pipeline-store";
import { useProjectStore } from "@/stores/project-store";
import { Button } from "@/components/ui/button";

export default function PipelinePage() {
  const activeProject = useProjectStore((s) => s.activeProject);
  const currentStep = usePipelineStore((s) => s.currentStep);

  if (!activeProject) {
    return <ProjectSelectorDialog />;
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <Stepper currentStep={currentStep} />
        <Button variant="outline">Visualize Data</Button>
      </div>

      {currentStep === "search" && <StepSearch />}
      {currentStep === "topics" && <StepTopicModelling />}
      {currentStep === "label" && <StepLabelDataset />}
    </div>
  );
}
