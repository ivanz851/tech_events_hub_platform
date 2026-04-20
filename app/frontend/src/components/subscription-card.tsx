"use client";

import * as React from "react";
import { Trash2 } from "lucide-react";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useToast } from "@/hooks/use-toast";
import { deleteLinkAction } from "@/lib/client-actions";
import type { LinkResponse } from "@/lib/api";

interface SubscriptionCardProps {
  link: LinkResponse;
  onDeleted: (url: string) => void;
}

const FORMAT_LABELS: Record<string, string> = {
  offline: "Оффлайн",
  online: "Онлайн",
  hybrid: "Гибрид",
};

export function SubscriptionCard({ link, onDeleted }: SubscriptionCardProps) {
  const { toast } = useToast();
  const [deleting, setDeleting] = React.useState(false);

  async function handleDelete() {
    if (!confirm(`Удалить отслеживание: ${link.link}?`)) return;
    setDeleting(true);
    onDeleted(link.link);
    const result = await deleteLinkAction(link.link);
    if (!result.success) {
      toast({
        variant: "destructive",
        title: "Ошибка",
        description: result.error ?? "Не удалось удалить ресурс",
      });
    }
    setDeleting(false);
  }

  const filters = link.filters;
  const hasFilters =
    filters &&
    (filters.city ||
      filters.format ||
      filters.is_free ||
      filters.date_from ||
      filters.date_to ||
      (filters.categories && filters.categories.length > 0));

  const hostname = (() => {
    try {
      return new URL(link.link).hostname;
    } catch {
      return link.link;
    }
  })();

  return (
    <Card className="relative flex flex-col">
      <CardHeader className="pb-2 pr-12">
        <a
          href={link.link}
          target="_blank"
          rel="noopener noreferrer"
          className="text-sm font-medium text-primary hover:underline break-all"
        >
          {hostname}
        </a>
        <p className="text-xs text-muted-foreground break-all">{link.link}</p>
      </CardHeader>

      <Button
        variant="ghost"
        size="icon"
        className="absolute right-2 top-2 h-8 w-8 text-muted-foreground hover:text-destructive"
        onClick={handleDelete}
        disabled={deleting}
        aria-label="Удалить"
      >
        <Trash2 className="h-4 w-4" />
      </Button>

      {hasFilters && (
        <CardContent className="pt-0">
          <div className="flex flex-wrap gap-1">
            {filters?.city && (
              <Badge variant="secondary">🏙️ {filters.city}</Badge>
            )}
            {filters?.format && (
              <Badge variant="secondary">
                {FORMAT_LABELS[filters.format] ?? filters.format}
              </Badge>
            )}
            {filters?.is_free && (
              <Badge variant="default">Бесплатно</Badge>
            )}
            {filters?.date_from && (
              <Badge variant="outline">с {filters.date_from}</Badge>
            )}
            {filters?.date_to && (
              <Badge variant="outline">до {filters.date_to}</Badge>
            )}
            {filters?.categories?.map((cat) => (
              <Badge key={cat} variant="secondary">
                {cat}
              </Badge>
            ))}
          </div>
        </CardContent>
      )}
    </Card>
  );
}
