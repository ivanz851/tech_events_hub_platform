"use client";

import * as React from "react";
import { PlusCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { SubscriptionCard } from "@/components/subscription-card";
import { AddSubscriptionDialog } from "@/components/add-subscription-dialog";
import type { LinkResponse } from "@/lib/api";

interface DashboardContentProps {
  initialLinks: LinkResponse[];
}

export function DashboardContent({ initialLinks }: DashboardContentProps) {
  const [links, setLinks] = React.useState<LinkResponse[]>(initialLinks);

  function handleDeleted(url: string) {
    setLinks((prev) => prev.filter((l) => l.link !== url));
  }

  const addTrigger = (
    <Button>
      <PlusCircle className="mr-2 h-4 w-4" />
      Добавить ресурс
    </Button>
  );

  if (links.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center gap-4 py-24 text-center">
        <p className="text-lg text-muted-foreground">Вы ещё ничего не отслеживаете</p>
        <AddSubscriptionDialog trigger={addTrigger} />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-end">
        <AddSubscriptionDialog trigger={addTrigger} />
      </div>
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
        {links.map((link) => (
          <SubscriptionCard key={link.link} link={link} onDeleted={handleDeleted} />
        ))}
      </div>
    </div>
  );
}
