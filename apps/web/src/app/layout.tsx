import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Workkbot | Enterprise AI Workspace",
  description: "Enterprise conversational assistant with dynamic MCP tools, Google Workspace, and Zoho integrations.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="h-full">
      <body className="h-full antialiased selection:bg-amber-100 selection:text-amber-900 dark:selection:bg-amber-950 dark:selection:text-amber-200">
        {children}
      </body>
    </html>
  );
}
