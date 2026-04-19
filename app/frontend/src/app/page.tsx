import Link from "next/link";
import { Zap, Bell, Search, Filter } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

const FEATURES = [
  {
    icon: Search,
    title: "Мониторинг источников",
    description: "Следите за Telegram-каналами и сайтами, где публикуются анонсы митапов, конференций и хакатонов.",
  },
  {
    icon: Filter,
    title: "Умные фильтры",
    description: "Настройте фильтры по городу, категории, формату и цене — получайте только то, что важно вам.",
  },
  {
    icon: Bell,
    title: "Омниканальные уведомления",
    description: "Получайте уведомления в Telegram и на Email — выбирайте удобный канал или оба сразу.",
  },
];

export default function HomePage() {
  return (
    <div className="flex flex-col">
      <section className="py-24 px-4">
        <div className="mx-auto max-w-3xl text-center">
          <div className="flex items-center justify-center gap-2 mb-6">
            <Zap className="h-8 w-8 text-primary" />
            <h1 className="text-4xl font-bold tracking-tight">TechEventsHub</h1>
          </div>
          <p className="text-xl text-muted-foreground mb-8">
            Не пропустите ни один технический митап, конференцию или хакатон.
            Умный мониторинг и персональные уведомления.
          </p>
          <Button asChild size="lg">
            <Link href="/api/auth/login">Войти через Яндекс</Link>
          </Button>
        </div>
      </section>

      <section className="py-16 px-4 bg-muted/30">
        <div className="mx-auto max-w-5xl">
          <h2 className="text-2xl font-bold text-center mb-10">Возможности</h2>
          <div className="grid gap-6 md:grid-cols-3">
            {FEATURES.map(({ icon: Icon, title, description }) => (
              <Card key={title}>
                <CardHeader>
                  <Icon className="h-8 w-8 text-primary mb-2" />
                  <CardTitle className="text-lg">{title}</CardTitle>
                </CardHeader>
                <CardContent>
                  <CardDescription>{description}</CardDescription>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </section>
    </div>
  );
}
