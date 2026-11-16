import type { Metadata } from "next";
import "./globals.css";
import { AuthProvider } from "@/lib/auth";

export const metadata: Metadata = {
  title: "منصة صفير القابضة | Safir Holding Platform",
  description: "منصة إدارة الشركات القابضة",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  // Arabic is the primary language: RTL by default. The client provider updates
  // lang/dir when the user switches to English.
  return (
    <html lang="ar" dir="rtl" suppressHydrationWarning>
      <body>
        <AuthProvider>{children}</AuthProvider>
      </body>
    </html>
  );
}
