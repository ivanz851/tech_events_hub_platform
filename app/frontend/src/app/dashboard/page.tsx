import { LayoutDashboard } from "lucide-react";

export default function DashboardPage() {
  return (
    <div className="container mx-auto max-w-7xl px-4 py-12">
      <div className="flex items-center gap-3 mb-8">
        <LayoutDashboard className="h-7 w-7" />
        <h1 className="text-3xl font-bold">Дашборд</h1>
      </div>
      <p className="text-muted-foreground">
        Управление подписками будет доступно в следующей версии.
      </p>
    </div>
  );
}
