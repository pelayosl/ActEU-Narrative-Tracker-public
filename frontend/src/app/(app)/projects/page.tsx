"use client";

import { useRouter } from "next/navigation";
import { ProjectList } from "@/components/projects/project-list";
import { Button } from "@/components/ui/button";
import { useProjectStore } from "@/stores/project-store";

export default function ProjectsPage() {
  const router = useRouter();
  const setActiveProject = useProjectStore((s) => s.setActiveProject);

  // "+ New Pipeline" → open the Pipeline with the project selection/creation dialog
  // (clearing the active project makes the pipeline show its selector).
  function newPipeline() {
    setActiveProject(null);
    router.push("/pipeline");
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold text-ink">Project Library</h1>
        <Button onClick={newPipeline}>+ New Pipeline</Button>
      </div>
      <ProjectList />
    </div>
  );
}
