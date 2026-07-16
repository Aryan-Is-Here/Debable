"use client";

import { useForm, Controller } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { toast } from "sonner";
import { useRouter } from "next/navigation";
import { Loader2 } from "lucide-react";

import {
  createTopicSchema,
  type CreateTopicInput,
} from "@/lib/validation/topic";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import {
  Field,
  FieldDescription,
  FieldError,
  FieldGroup,
  FieldLabel,
} from "@/components/ui/field";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

interface CreateTopicFormProps {
  /** Category options offered in the select. */
  categories: string[];
}

/**
 * Create Topic form. Phase 1 is mock-only: a valid submit simulates success
 * (toast + redirect to Browse) without hitting a backend. The zod schema is
 * shared and will back the real API call in a later phase.
 */
export function CreateTopicForm({ categories }: CreateTopicFormProps) {
  const router = useRouter();

  const {
    register,
    handleSubmit,
    control,
    formState: { errors, isSubmitting },
  } = useForm<CreateTopicInput>({
    resolver: zodResolver(createTopicSchema),
    defaultValues: { title: "", description: "", category: "" },
  });

  async function onSubmit(values: CreateTopicInput) {
    // Mock submit — no backend in Phase 1. Simulate a short network delay.
    await new Promise((resolve) => setTimeout(resolve, 600));
    toast.success("Topic created", { description: values.title });
    router.push("/browse");
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} noValidate>
      <FieldGroup>
        {/* Title */}
        <Field data-invalid={!!errors.title}>
          <FieldLabel htmlFor="title">Title</FieldLabel>
          <Input
            id="title"
            placeholder="e.g. Should social media have a minimum age?"
            aria-invalid={!!errors.title}
            {...register("title")}
          />
          <FieldDescription>
            A clear, debatable statement or question.
          </FieldDescription>
          <FieldError errors={[errors.title]} />
        </Field>

        {/* Description */}
        <Field data-invalid={!!errors.description}>
          <FieldLabel htmlFor="description">Description</FieldLabel>
          <Textarea
            id="description"
            rows={4}
            placeholder="Add context, framing, or the core question at stake."
            aria-invalid={!!errors.description}
            {...register("description")}
          />
          <FieldError errors={[errors.description]} />
        </Field>

        {/* Category */}
        <Field data-invalid={!!errors.category}>
          <FieldLabel htmlFor="category">Category</FieldLabel>
          <Controller
            control={control}
            name="category"
            render={({ field }) => (
              <Select value={field.value} onValueChange={field.onChange}>
                <SelectTrigger id="category" aria-invalid={!!errors.category}>
                  <SelectValue placeholder="Choose a category" />
                </SelectTrigger>
                <SelectContent>
                  {categories.map((c) => (
                    <SelectItem key={c} value={c}>
                      {c}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            )}
          />
          <FieldError errors={[errors.category]} />
        </Field>

        <div className="flex gap-3">
          <Button type="submit" disabled={isSubmitting}>
            {isSubmitting && <Loader2 className="size-4 animate-spin" />}
            Create topic
          </Button>
          <Button
            type="button"
            variant="ghost"
            disabled={isSubmitting}
            onClick={() => router.push("/browse")}
          >
            Cancel
          </Button>
        </div>
      </FieldGroup>
    </form>
  );
}
