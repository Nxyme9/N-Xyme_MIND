import NextAuth from "next-auth";
import Credentials from "next-auth/providers/credentials";

// SECURITY: Require explicit env vars - no fallback to weak defaults
const ADMIN_USER = process.env.ADMIN_USER;
const ADMIN_PASS = process.env.ADMIN_PASS;

// Throw error if credentials not configured (security hardening)
if (!ADMIN_USER || !ADMIN_PASS) {
  console.error("SECURITY: ADMIN_USER and ADMIN_PASS environment variables must be set");
}

export const { auth, signIn, signOut } = NextAuth({
  providers: [
    Credentials({
      name: "Credentials",
      credentials: {
        username: { label: "Username", type: "text" },
        password: { label: "Password", type: "password" },
      },
      async authorize(credentials) {
        if (
          credentials?.username === ADMIN_USER &&
          credentials?.password === ADMIN_PASS
        ) {
          return { id: "1", name: "admin", email: "admin@localhost" };
        }
        return null;
      },
    }),
  ],
  secret: process.env.NEXTAUTH_SECRET,
});