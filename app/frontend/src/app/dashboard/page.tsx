import { LayoutDashboard } from "lucide-react";
import { getLinks } from "@/lib/api";
import { DashboardContent } from "./dashboard-content";

export default async function DashboardPage() {
  let links = [];
  try {
    links = await getLinks();
  } catch {
    links = [];
  }

  return (
    <div className="container mx-auto max-w-7xl px-4 py-12">
      <div className="flex items-center gap-3 mb-8">
        <LayoutDashboard className="h-7 w-7" />
        <h1 className="text-3xl font-bold">Дашборд</h1>
      </div>
      <DashboardContent initialLinks={links} />
    </div>
  );
}
