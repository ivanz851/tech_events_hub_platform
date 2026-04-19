"use client";

import { useState } from "react";
import { MessageCircle, Mail, Link2 } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Switch } from "@/components/ui/switch";
import { Button } from "@/components/ui/button";
import { useToast } from "@/hooks/use-toast";
import { updateSettings, generateLinkToken } from "@/lib/client-actions";

interface ProfileSettingsProps {
  initialSettings: {
    notify_telegram: boolean;
    notify_email: boolean;
  };
  providers: string[];
}

export function ProfileSettings({ initialSettings, providers }: ProfileSettingsProps) {
  const [notifyTelegram, setNotifyTelegram] = useState(initialSettings.notify_telegram);
  const [notifyEmail, setNotifyEmail] = useState(initialSettings.notify_email);
  const [linkToken, setLinkToken] = useState<string | null>(null);
  const [isGenerating, setIsGenerating] = useState(false);
  const { toast } = useToast();

  const hasTelegram = providers.includes("telegram");
  const botUsername = process.env.NEXT_PUBLIC_BOT_USERNAME ?? "TechEventsHubBot";

  async function handleToggleTelegram(checked: boolean) {
    setNotifyTelegram(checked);
    try {
      await updateSettings({ notify_telegram: checked });
      toast({ title: "Настройки сохранены" });
    } catch {
      setNotifyTelegram(!checked);
      toast({ title: "Ошибка", description: "Не удалось сохранить настройки", variant: "destructive" });
    }
  }

  async function handleToggleEmail(checked: boolean) {
    setNotifyEmail(checked);
    try {
      await updateSettings({ notify_email: checked });
      toast({ title: "Настройки сохранены" });
    } catch {
      setNotifyEmail(!checked);
      toast({ title: "Ошибка", description: "Не удалось сохранить настройки", variant: "destructive" });
    }
  }

  async function handleGenerateLinkToken() {
    setIsGenerating(true);
    try {
      const token = await generateLinkToken();
      setLinkToken(token);
    } catch {
      toast({ title: "Ошибка", description: "Не удалось получить токен привязки", variant: "destructive" });
    } finally {
      setIsGenerating(false);
    }
  }

  const telegramDeepLink = linkToken
    ? `https://t.me/${botUsername}?start=${linkToken}`
    : null;

  return (
    <>
      <Card>
        <CardHeader>
          <CardTitle>Уведомления</CardTitle>
          <CardDescription>Выберите, по каким каналам получать уведомления о новых событиях</CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <MessageCircle className="h-5 w-5 text-muted-foreground" />
              <div>
                <p className="text-sm font-medium">Уведомления в Telegram</p>
                <p className="text-xs text-muted-foreground">Получать уведомления через Telegram-бота</p>
              </div>
            </div>
            <Switch
              checked={notifyTelegram}
              onCheckedChange={handleToggleTelegram}
              disabled={!hasTelegram}
              aria-label="Уведомления в Telegram"
            />
          </div>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Mail className="h-5 w-5 text-muted-foreground" />
              <div>
                <p className="text-sm font-medium">Уведомления на Email</p>
                <p className="text-xs text-muted-foreground">Получать уведомления по электронной почте</p>
              </div>
            </div>
            <Switch
              checked={notifyEmail}
              onCheckedChange={handleToggleEmail}
              aria-label="Уведомления на Email"
            />
          </div>
        </CardContent>
      </Card>

      {!hasTelegram && (
        <Card>
          <CardHeader>
            <CardTitle>Привязать Telegram</CardTitle>
            <CardDescription>
              Привяжите Telegram-аккаунт, чтобы получать уведомления в боте
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {telegramDeepLink ? (
              <div className="space-y-3">
                <p className="text-sm text-muted-foreground">
                  Откройте ссылку ниже в Telegram для привязки аккаунта:
                </p>
                <a
                  href={telegramDeepLink}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-2 text-sm text-primary hover:underline break-all"
                >
                  <Link2 className="h-4 w-4 shrink-0" />
                  {telegramDeepLink}
                </a>
              </div>
            ) : (
              <Button
                onClick={handleGenerateLinkToken}
                disabled={isGenerating}
                variant="outline"
              >
                {isGenerating ? "Генерация..." : "Привязать Telegram"}
              </Button>
            )}
          </CardContent>
        </Card>
      )}
    </>
  );
}
