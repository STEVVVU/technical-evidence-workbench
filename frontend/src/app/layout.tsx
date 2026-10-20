import "@/styles/globals.css";

import { type Metadata } from "next";

import { ThemeProvider } from "@/components/theme-provider";
import { ArtifactDraftsProvider } from "@/core/artifacts/draft-context";
import { DEFAULT_LOCALE } from "@/core/i18n/locale";
import { WORKBENCH_NAME } from "@/core/workbench";

export const metadata: Metadata = {
  title: WORKBENCH_NAME,
  description:
    "Technical investigations with saved sources, traceable claims, and human-reviewed evidence reports.",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html
      lang={DEFAULT_LOCALE}
      suppressContentEditableWarning
      suppressHydrationWarning
    >
      <body>
        <ThemeProvider attribute="class" enableSystem disableTransitionOnChange>
          <ArtifactDraftsProvider>{children}</ArtifactDraftsProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
