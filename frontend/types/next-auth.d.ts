import { DefaultSession } from "next-auth";

declare module "next-auth" {
  interface Session {
    user: {
      studentId?: string | number;
    } & DefaultSession["user"];
  }
}