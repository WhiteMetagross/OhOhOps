"use client";

import { useSyncExternalStore } from "react";
import { Moon, Sun } from "lucide-react";

type Theme = "dark" | "light";

function setDocumentTheme(theme: Theme) {
  document.documentElement.dataset.theme = theme;
  document.documentElement.style.colorScheme = theme;
  localStorage.setItem("ohohops-theme", theme);
  window.dispatchEvent(new Event("ohohops-theme-change"));
}

export function ThemeToggle() {
  const theme = useSyncExternalStore<Theme>(
    (onStoreChange) => {
      window.addEventListener("ohohops-theme-change", onStoreChange);
      return () => window.removeEventListener("ohohops-theme-change", onStoreChange);
    },
    () => (document.documentElement.dataset.theme === "light" ? "light" : "dark"),
    () => "dark",
  );

  const nextTheme = theme === "dark" ? "light" : "dark";

  return (
    <button
      type="button"
      onClick={() => {
        setDocumentTheme(nextTheme);
      }}
      aria-label={`Switch to ${nextTheme} mode`}
      title={`Switch to ${nextTheme} mode`}
      className="sunfire-button-muted inline-flex items-center gap-2 px-3 py-2 text-sm"
    >
      {theme === "dark" ? (
        <Sun className="h-4 w-4" aria-hidden="true" />
      ) : (
        <Moon className="h-4 w-4" aria-hidden="true" />
      )}
      {theme === "dark" ? "Light" : "Dark"}
    </button>
  );
}
