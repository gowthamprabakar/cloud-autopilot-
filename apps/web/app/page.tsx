import { redirect } from "next/navigation";

export default function HomePage() {
  // In Phase 1, root redirects to dashboard (client-side auth handles redirect to login)
  redirect("/dashboard");
}
