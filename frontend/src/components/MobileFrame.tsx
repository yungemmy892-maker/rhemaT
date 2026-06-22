import type { ReactNode } from "react";

export function MobileFrame({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-screen bg-background relative overflow-x-hidden">
      {/* Ambient gradient backdrop */}
      <div className="pointer-events-none fixed inset-0 -z-10">
        <div className="absolute -top-32 -left-24 h-80 w-80 rounded-full bg-primary/20 blur-3xl animate-float-slow" />
        <div className="absolute top-1/3 -right-24 h-72 w-72 rounded-full bg-accent/40 blur-3xl animate-float-slow [animation-delay:-4s]" />
      </div>
      <div className="mx-auto max-w-md min-h-screen px-5 pt-6 pb-32">{children}</div>
    </div>
  );
}
