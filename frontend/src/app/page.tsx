import { redirect } from "next/navigation";

// Onboarding is the entry point. From there the user chooses to enter the
// online SRE (SaaS) dashboard, which lives at /dashboard.
export default function Home() {
  redirect("/onboarding");
}
