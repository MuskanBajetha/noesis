"use client";

import { useSession } from "next-auth/react";
import { useRouter } from "next/navigation";
import { useEffect } from "react";

/**
 * Single source of truth for "who is logged in" across the app.
 * Redirects to /auth if there's no session. Returns null while loading.
 */
export function useStudentId(): number | null {
  const { data: session, status } = useSession();
  const router = useRouter();

  useEffect(() => {
    if (status === "unauthenticated") {
      router.push("/auth");
    }
  }, [status]);

  if (status !== "authenticated" || !session?.user) return null;
  const id = (session.user as any).studentId;
  return id ? Number(id) : null;
}