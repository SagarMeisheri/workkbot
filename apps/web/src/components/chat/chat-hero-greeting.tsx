"use client";

import React from "react";

interface ChatHeroGreetingProps {
  user: {
    first_name?: string;
    email?: string;
  } | null;
}

export function ChatHeroGreeting({ user }: ChatHeroGreetingProps) {
  if (!user) {
    return (
      <div className="flex flex-col items-center justify-center my-8 text-center">
        <h1 className="text-3xl sm:text-4xl font-semibold tracking-tight text-foreground">
          How can I help you today?
        </h1>
        <p className="text-sm text-muted-foreground mt-2 max-w-md">
          Ask questions, compose documents, query connected tools, or analyze data.
        </p>
      </div>
    );
  }

  const displayName = user.first_name || (user.email ? user.email.split("@")[0] : "sagar");

  return (
    <div className="flex items-center justify-center gap-3 my-8 text-center animate-in fade-in duration-300">
      <span className="text-amber-600 dark:text-amber-500 text-3xl select-none font-serif">✳</span>
      <h1 className="text-3xl sm:text-4xl font-serif font-normal text-foreground tracking-tight">
        Back at it, {displayName}
      </h1>
    </div>
  );
}
