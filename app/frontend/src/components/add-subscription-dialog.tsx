"use client";

import * as React from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { format } from "date-fns";
import { CalendarIcon, Loader2, X } from "lucide-react";
import type { DateRange } from "react-day-picker";

import { subscriptionSchema, type SubscriptionFormData } from "@/lib/validations";
import { addLinkAction } from "@/lib/client-actions";
import type { AddLinkRequest, SubscriptionFilters } from "@/lib/api";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Calendar } from "@/components/ui/calendar";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
  DialogFooter,
} from "@/components/ui/dialog";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { Switch } from "@/components/ui/switch";
import { useToast } from "@/hooks/use-toast";

interface AddSubscriptionDialogProps {
  trigger?: React.ReactNode;
}

function buildFilters(data: SubscriptionFormData): SubscriptionFilters | null {
  const filters: SubscriptionFilters = {};

  if (data.city?.trim()) filters.city = data.city.trim();
  if (data.format) filters.format = data.format;
  if (data.is_free !== undefined && data.is_free !== null) filters.is_free = data.is_free;
  if (data.date_from) filters.date_from = format(data.date_from, "yyyy-MM-dd");
  if (data.date_to) filters.date_to = format(data.date_to, "yyyy-MM-dd");
  if (data.categories.length > 0) filters.categories = data.categories;

  return Object.keys(filters).length > 0 ? filters : null;
}

export function AddSubscriptionDialog({ trigger }: AddSubscriptionDialogProps) {
  const [open, setOpen] = React.useState(false);
  const [dateRange, setDateRange] = React.useState<DateRange | undefined>(undefined);
  const [categoryInput, setCategoryInput] = React.useState("");
  const { toast } = useToast();

  const form = useForm<SubscriptionFormData>({
    resolver: zodResolver(subscriptionSchema),
    defaultValues: {
      link: "",
      city: "",
      is_free: false,
      categories: [],
    },
  });

  function handleDateRangeSelect(range: DateRange | undefined) {
    setDateRange(range);
    form.setValue("date_from", range?.from);
    form.setValue("date_to", range?.to);
  }

  function handleCategoryKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === "Enter") {
      e.preventDefault();
      const trimmed = categoryInput.trim();
      if (!trimmed) return;
      const current = form.getValues("categories");
      if (!current.includes(trimmed)) {
        form.setValue("categories", [...current, trimmed]);
      }
      setCategoryInput("");
    }
  }

  function removeCategory(cat: string) {
    const current = form.getValues("categories");
    form.setValue(
      "categories",
      current.filter((c) => c !== cat)
    );
  }

  async function onSubmit(data: SubscriptionFormData) {
    const payload: AddLinkRequest = {
      link: data.link,
      filters: buildFilters(data),
    };

    const result = await addLinkAction(payload);

    if (!result.success) {
      toast({
        variant: "destructive",
        title: "Ошибка",
        description: result.error ?? "Не удалось добавить ресурс",
      });
      return;
    }

    toast({ title: "Готово", description: "Ресурс добавлен в отслеживание" });
    form.reset();
    setDateRange(undefined);
    setCategoryInput("");
    setOpen(false);
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        {trigger ?? <Button>Добавить ресурс</Button>}
      </DialogTrigger>
      <DialogContent className="sm:max-w-[540px]">
        <DialogHeader>
          <DialogTitle>Добавить ресурс для отслеживания</DialogTitle>
        </DialogHeader>

        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
            <FormField
              control={form.control}
              name="link"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>URL ресурса</FormLabel>
                  <FormControl>
                    <Input placeholder="https://t.me/it_events" {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="format"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Формат мероприятий</FormLabel>
                  <Select onValueChange={field.onChange} value={field.value ?? ""}>
                    <FormControl>
                      <SelectTrigger>
                        <SelectValue placeholder="Любой формат" />
                      </SelectTrigger>
                    </FormControl>
                    <SelectContent>
                      <SelectItem value="offline">Оффлайн</SelectItem>
                      <SelectItem value="online">Онлайн</SelectItem>
                      <SelectItem value="hybrid">Гибрид</SelectItem>
                    </SelectContent>
                  </Select>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="city"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Город</FormLabel>
                  <FormControl>
                    <Input placeholder="Москва" {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="is_free"
              render={({ field }) => (
                <FormItem className="flex flex-row items-center justify-between rounded-lg border p-3">
                  <FormLabel className="mb-0">Только бесплатные мероприятия</FormLabel>
                  <FormControl>
                    <Switch checked={field.value ?? false} onCheckedChange={field.onChange} />
                  </FormControl>
                </FormItem>
              )}
            />

            <FormItem>
              <FormLabel>Диапазон дат</FormLabel>
              <Popover>
                <PopoverTrigger asChild>
                  <Button variant="outline" className="w-full justify-start text-left font-normal">
                    <CalendarIcon className="mr-2 h-4 w-4" />
                    {dateRange?.from ? (
                      dateRange.to ? (
                        <>
                          {format(dateRange.from, "dd.MM.yyyy")} –{" "}
                          {format(dateRange.to, "dd.MM.yyyy")}
                        </>
                      ) : (
                        format(dateRange.from, "dd.MM.yyyy")
                      )
                    ) : (
                      <span className="text-muted-foreground">Выберите период</span>
                    )}
                  </Button>
                </PopoverTrigger>
                <PopoverContent className="w-auto p-0" align="start">
                  <Calendar
                    mode="range"
                    selected={dateRange}
                    onSelect={handleDateRangeSelect}
                    numberOfMonths={2}
                  />
                </PopoverContent>
              </Popover>
            </FormItem>

            <FormField
              control={form.control}
              name="categories"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Категории</FormLabel>
                  <FormControl>
                    <Input
                      placeholder="Введите категорию и нажмите Enter"
                      value={categoryInput}
                      onChange={(e) => setCategoryInput(e.target.value)}
                      onKeyDown={handleCategoryKeyDown}
                      aria-describedby={undefined}
                      id={undefined}
                    />
                  </FormControl>
                  {field.value.length > 0 && (
                    <div className="flex flex-wrap gap-1 pt-1">
                      {field.value.map((cat) => (
                        <Badge key={cat} variant="secondary" className="gap-1 pr-1">
                          {cat}
                          <button
                            type="button"
                            onClick={() => removeCategory(cat)}
                            className="rounded-full hover:bg-muted-foreground/20"
                          >
                            <X className="h-3 w-3" />
                          </button>
                        </Badge>
                      ))}
                    </div>
                  )}
                  <FormMessage />
                </FormItem>
              )}
            />

            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setOpen(false)}>
                Отмена
              </Button>
              <Button type="submit" disabled={form.formState.isSubmitting}>
                {form.formState.isSubmitting && (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                )}
                Сохранить
              </Button>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  );
}
