import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "katex/dist/katex.min.css";
import "./globals.css";
import { AuthProvider } from "@/src/contexts/AuthContext";
import { NotificationProvider } from "@/src/contexts/NotificationContext";
import { CourseProvider } from "@/src/contexts/CourseContext";
import { THEME_INIT_SCRIPT } from "@/src/utils/theme";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  // German first, like the server render of the public pages; the pages set
  // <html lang> to the visitor's language on hydration.
  title: "Computor – Lernplattform für Programmierung",
  description: "Programmieren lernen mit interaktiven Kursen, automatischen Tests und gemeinsamem Arbeiten",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="de" suppressHydrationWarning>
      <head>
        {/* Before first paint — see THEME_INIT_SCRIPT for why this is inline. */}
        <script dangerouslySetInnerHTML={{ __html: THEME_INIT_SCRIPT }} />
      </head>
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased`}
      >
        <AuthProvider>
          <NotificationProvider>
            {/*
              Above every page, not inside AuthenticatedLayout: pages call
              useCourseCrumbs before they render that layout, and below it
              they only ever saw the context's default, so the breadcrumb read
              "Kurs" where the course's name belonged.
            */}
            <CourseProvider>{children}</CourseProvider>
          </NotificationProvider>
        </AuthProvider>
      </body>
    </html>
  );
}
