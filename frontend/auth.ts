import NextAuth from "next-auth";
import Google from "next-auth/providers/google";
import Credentials from "next-auth/providers/credentials";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000/api";

export const { handlers, signIn, signOut, auth } = NextAuth({
  providers: [
    Google({
      clientId: process.env.GOOGLE_CLIENT_ID,
      clientSecret: process.env.GOOGLE_CLIENT_SECRET,
    }),
    Credentials({
      credentials: {
        email: { label: "Email", type: "email" },
        password: { label: "Password", type: "password" },
        mode: { label: "Mode", type: "text" }, // "login" or "register"
        name: { label: "Name", type: "text" },
      },
      async authorize(credentials) {
        const { email, password, mode, name } = credentials as {
          email: string; password: string; mode: string; name?: string;
        };

        const endpoint = mode === "register" ? "/auth/register" : "/auth/login";
        const body = mode === "register" ? { name, email, password } : { email, password };

        const res = await fetch(`${API_BASE}${endpoint}`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
        });

        if (!res.ok) return null;

        const data = await res.json();
        return {
          id: String(data.student_id),
          name: data.name,
          email: data.email,
        };
      },
    }),
  ],
  callbacks: {
    async signIn({ user, account }) {
      // Google sign-ins need to be find-or-created in our own students table
      if (account?.provider === "google" && user.email) {
        const res = await fetch(`${API_BASE}/auth/oauth-login`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ name: user.name, email: user.email }),
        });
        if (!res.ok) return false;
        const data = await res.json();
        // Stash the real backend student_id so the JWT callback can pick it up
        (user as any).backendStudentId = data.student_id;
      }
      return true;
    },
    async jwt({ token, user }) {
      if (user) {
        token.studentId = (user as any).backendStudentId || user.id;
      }
      return token;
    },
    async session({ session, token }) {
      if (session.user) {
        (session.user as any).studentId = token.studentId;
      }
      return session;
    },
  },
  pages: {
    signIn: "/auth",
  },
  session: { strategy: "jwt" },
});