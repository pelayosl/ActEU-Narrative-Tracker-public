"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { BarChart3 } from "lucide-react";
import { Stepper } from "@/components/pipeline/stepper";
import { StepSearch } from "@/components/pipeline/step-search";
import { StepTopicModelling } from "@/components/pipeline/step-topic-modelling";
import { StepLabelDataset } from "@/components/pipeline/step-label-dataset";
import { ProjectSelectorDialog } from "@/components/projects/project-selector-dialog";
import { usePipelineStore } from "@/stores/pipeline-store";
import { useProjectStore } from "@/stores/project-store";
import { buildVisualiserPrefill, useVisualiserStore } from "@/stores/visualiser-store";
import { Button } from "@/components/ui/button";

export default function PipelinePage() {
  const router = useRouter();
  const activeProject = useProjectStore((s) => s.activeProject);
  const currentStep = usePipelineStore((s) => s.currentStep);
  const searchQuery = usePipelineStore((s) => s.searchQuery);
  const trainedClassifier = usePipelineStore((s) => s.trainedClassifier);
  const hydrateFromProject = usePipelineStore((s) => s.hydrateFromProject);
  const setPrefill = useVisualiserStore((s) => s.setPrefill);

  // On entering the pipeline, resume from the project's pending_pipeline.
  useEffect(() => {
    if (activeProject) hydrateFromProject(activeProject);
  }, [activeProject, hydrateFromProject]);

  function goToVisualiser() {
    setPrefill(buildVisualiserPrefill(searchQuery, trainedClassifier));
    router.push("/visualiser");
  }

  if (!activeProject) {
    return <ProjectSelectorDialog />;
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <Stepper currentStep={currentStep} />
        <Button variant="outline" onClick={goToVisualiser} className="shrink-0">
          <BarChart3 className="mr-1.5 h-4 w-4" />
          Visualise Data
        </Button>
      </div>

      {currentStep === "search" && <StepSearch />}
      {currentStep === "topics" && <StepTopicModelling />}
      {currentStep === "label" && <StepLabelDataset />}
    </div>
  );
}
