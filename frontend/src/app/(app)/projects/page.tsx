import { ProjectList } from "@/components/projects/project-list";
import { Button } from "@/components/ui/button";

export default function ProjectsPage() {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold text-ink">Project Library</h1>
        <Button>+ New Pipeline</Button>
      </div>
      <ProjectList />
    </div>
  );
}
