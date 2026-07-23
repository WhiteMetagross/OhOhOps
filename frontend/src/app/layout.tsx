import type { Metadata, Viewport } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: {
    default: "OhOhOps",
    template: "%s | OhOhOps",
  },
  description: "Autonomous SRE operations, incident repair, and system observability.",
  icons: {
    icon: "/ohohops-logo.png",
    apple: "/ohohops-logo.png",
  },
};

export const viewport: Viewport = {
  themeColor: [
    { media: "(prefers-color-scheme: dark)", color: "#160805" },
    { media: "(prefers-color-scheme: light)", color: "#fff2dc" },
  ],
  colorScheme: "dark light",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      data-theme="dark"
      suppressHydrationWarning
      className="antialiased"
    >
      <head>
        <script
          dangerouslySetInnerHTML={{
            __html: `(function(){try{var saved=localStorage.getItem("ohohops-theme");var theme=saved==="light"||saved==="dark"?saved:(matchMedia("(prefers-color-scheme: light)").matches?"light":"dark");document.documentElement.dataset.theme=theme;document.documentElement.style.colorScheme=theme;}catch(_){}})();`,
          }}
        />
      </head>
      <body>{children}</body>
    </html>
  );
}
