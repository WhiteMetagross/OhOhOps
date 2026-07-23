import Image from "next/image";
import Link from "next/link";
import { BookOpenText, Gauge, KeyRound } from "lucide-react";
import { HealthStrip } from "./HealthStrip";
import { ThemeToggle } from "./ThemeToggle";

type BrandHeaderProps = {
  eyebrow: string;
  title: string;
  description: string;
  showHealth?: boolean;
  showSettings?: boolean;
};

const navItems = [
  { href: "/dashboard", label: "Operations", icon: Gauge },
  { href: "/onboarding", label: "Setup", icon: BookOpenText },
];

export function BrandHeader({
  eyebrow,
  title,
  description,
  showHealth = false,
  showSettings = false,
}: BrandHeaderProps) {
  return (
    <header className="sunfire-card-strong overflow-hidden">
      <div className="flex flex-col gap-6 p-5 sm:p-7 lg:flex-row lg:items-center lg:justify-between">
        <div className="flex min-w-0 items-center gap-4">
          <div className="sunfire-icon-shell relative h-16 w-16 shrink-0 overflow-hidden rounded-2xl border border-primary/25 sm:h-20 sm:w-20">
            <Image
              src="/ohohops-logo.png"
              alt="OhOhOps phoenix logo"
              fill
              priority
              sizes="80px"
              className="object-cover object-center"
            />
          </div>
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
              <span className="sunfire-brand-rainbow text-sm font-black tracking-tight">
                OhOhOps
              </span>
              <p className="sunfire-kicker">{eyebrow}</p>
            </div>
            <h1
              className={`mt-1 text-3xl font-black tracking-tight sm:text-4xl ${
                title === "OhOhOps" ? "sunfire-brand-rainbow" : "sunfire-title"
              }`}
            >
              {title}
            </h1>
            <p className="mt-2 max-w-2xl text-sm leading-6 text-text-muted sm:text-[1rem]">
              {description}
            </p>
          </div>
        </div>

        <div className="flex flex-col items-start gap-4 lg:items-end">
          <nav aria-label="Primary navigation" className="flex flex-wrap items-center gap-2">
            {navItems.map(({ href, label, icon: Icon }) => (
              <Link
                key={href}
                href={href}
                className="sunfire-button-muted inline-flex items-center gap-2 px-3 py-2 text-sm"
              >
                <Icon className="h-4 w-4" aria-hidden="true" />
                {label}
              </Link>
            ))}
            {showSettings && (
              <Link
                href="/settings"
                className="sunfire-button-muted inline-flex items-center gap-2 px-3 py-2 text-sm"
              >
                <KeyRound className="h-4 w-4" aria-hidden="true" />
                Keys
              </Link>
            )}
            <ThemeToggle />
          </nav>
          {showHealth && (
            <div className="sunfire-glass-subtle rounded-full border border-primary/15 px-4 py-2">
              <HealthStrip />
            </div>
          )}
        </div>
      </div>
      <div className="h-px bg-gradient-to-r from-transparent via-primary/60 to-transparent" />
    </header>
  );
}
