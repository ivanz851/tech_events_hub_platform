import { getProfile } from "@/lib/api";
import { ProfileSettings } from "./profile-settings";
import { UserCircle } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export default async function ProfilePage() {
  let profile;
  try {
    profile = await getProfile();
  } catch {
    return (
      <div className="container mx-auto max-w-3xl px-4 py-12">
        <p className="text-destructive">Не удалось загрузить профиль. Попробуйте обновить страницу.</p>
      </div>
    );
  }

  const registeredAt = new Date(profile.created_at).toLocaleDateString("ru-RU", {
    year: "numeric",
    month: "long",
    day: "numeric",
  });

  return (
    <div className="container mx-auto max-w-3xl px-4 py-12 space-y-6">
      <div className="flex items-center gap-3 mb-8">
        <UserCircle className="h-7 w-7" />
        <h1 className="text-3xl font-bold">Профиль</h1>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Аккаунт</CardTitle>
          <CardDescription>Информация о вашем аккаунте</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="flex justify-between text-sm">
            <span className="text-muted-foreground">Email</span>
            <span>{profile.email ?? "Не указан"}</span>
          </div>
          <div className="flex justify-between text-sm">
            <span className="text-muted-foreground">Дата регистрации</span>
            <span>{registeredAt}</span>
          </div>
          <div className="flex justify-between text-sm">
            <span className="text-muted-foreground">Привязанные аккаунты</span>
            <span className="capitalize">{profile.providers.join(", ") || "Нет"}</span>
          </div>
        </CardContent>
      </Card>

      <ProfileSettings
        initialSettings={profile.settings}
        providers={profile.providers}
      />
    </div>
  );
}
