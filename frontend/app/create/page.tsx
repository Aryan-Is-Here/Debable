import type { Metadata } from "next";

import { CreateTopicForm } from "@/components/create-topic-form";
import { getCategories } from "@/lib/mock/topics";

export const metadata: Metadata = {
  title: "Create a topic",
  description: "Propose a new debate topic for others to argue.",
};

export default function CreatePage() {
  const categories = getCategories();

  return (
    <div className="mx-auto w-full max-w-2xl px-4 py-12 sm:px-6">
      <header className="mb-8">
        <h1 className="text-3xl font-semibold tracking-tight">Create a topic</h1>
        <p className="mt-1 text-muted-foreground">
          Propose a debate. Others can browse it and get matched to argue the
          other side.
        </p>
      </header>

      <CreateTopicForm categories={categories} />
    </div>
  );
}
