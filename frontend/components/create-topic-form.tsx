"use client";

import { useForm, Controller } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { toast } from "sonner";
import { useRouter } from "next/navigation";
import { Loader2 } from "lucide-react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { SignInButton, useAuth } from "@clerk/nextjs";

import {
  createTopicSchema,
  type CreateTopicInput,
} from "@/lib/validation/topic";
import { TOPIC_CATEGORIES } from "@/lib/constants/categories";
import { ApiError } from "@/services/api-client";
import { createTopic, topicKeys } from "@/services/topics";
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

/** Create Topic form. Submits to the real API and requires a signed-in user. */
export function CreateTopicForm() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const { isLoaded, isSignedIn, getToken } = useAuth();

  const {
    register,
    handleSubmit,
    control,
    setError,
    formState: { errors },
  } = useForm<CreateTopicInput>({
    resolver: zodResolver(createTopicSchema),
    // category is left undefined so the Select shows its placeholder; the enum schema has
    // no valid empty member to seed it with.
    defaultValues: { title: "", description: "" },
  });

  const { mutateAsync, isPending } = useMutation({
    mutationFn: async (values: CreateTopicInput) =>
      createTopic(values, await getToken()),
    onSuccess: async (topic) => {
      // Drop every cached topic list so Browse shows the new row immediately.
      await queryClient.invalidateQueries({ queryKey: topicKeys.all });
      toast.success("Topic created", { description: topic.title });
      router.push("/browse");
    },
  });

  async function onSubmit(values: CreateTopicInput) {
    try {
      await mutateAsync(values);
    } catch (error) {
      if (error instanceof ApiError && error.code === "conflict") {
        // Attach server-side conflicts to the field that caused them.
        setError("title", { message: error.message });
        return;
      }
      toast.error("Couldn't create topic", {
        description: error instanceof Error ? error.message : "Please try again.",
      });
    }
  }

  if (isLoaded && !isSignedIn) {
    return (
      <div className="flex flex-col items-start gap-3 rounded-lg border border-dashed border-border p-8">
        <p className="font-medium">Sign in to create a topic</p>
        <p className="text-sm text-muted-foreground">
          Topics are attributed to their creator, so we need to know who you are. Browsing
          stays open to everyone.
        </p>
        <SignInButton mode="modal">
          <Button>Sign in</Button>
        </SignInButton>
      </div>
    );
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
              <Select value={field.value ?? ""} onValueChange={field.onChange}>
                <SelectTrigger id="category" aria-invalid={!!errors.category}>
                  <SelectValue placeholder="Choose a category" />
                </SelectTrigger>
                <SelectContent>
                  {TOPIC_CATEGORIES.map((c) => (
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
          <Button type="submit" disabled={isPending}>
            {isPending && <Loader2 className="size-4 animate-spin" />}
            Create topic
          </Button>
          <Button
            type="button"
            variant="ghost"
            disabled={isPending}
            onClick={() => router.push("/browse")}
          >
            Cancel
          </Button>
        </div>
      </FieldGroup>
    </form>
  );
}
