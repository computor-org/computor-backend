import type { Metadata } from "next";
import { cookies, headers } from "next/headers";
import { Geist, Geist_Mono } from "next/font/google";
import "katex/dist/katex.min.css";
import "./globals.css";
import { AuthProvider } from "@/src/contexts/AuthContext";
import { NotificationProvider } from "@/src/contexts/NotificationContext";
import { CourseProvider } from "@/src/contexts/CourseContext";
import { THEME_INIT_SCRIPT } from "@/src/utils/theme";
import { APP_TITLES } from "@/src/utils/documentLanguage";
import { RequestLanguageProvider } from "@/src/contexts/RequestLanguageContext";
import {
  CHOSEN_LANGUAGE_COOKIE,
  cookieLanguage,
  DOCUMENT_LANGUAGE_HEADER,
  READING_LANGUAGE_COOKIE,
  requestLanguage,
  type ReadingLanguage,
  type RequestLanguage,
} from "@/src/utils/requestLanguage";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

const DESCRIPTIONS = {
  de: "Programmieren lernen mit interaktiven Kursen, automatischen Tests und gemeinsamem Arbeiten",
  en: "Learn programming with interactive courses, automatic tests and working together",
} as const;

async function readRequestLanguage(): Promise<RequestLanguage> {
  const [cookieStore, headerList] = await Promise.all([cookies(), headers()]);
  return requestLanguage(
    cookieStore.get(CHOSEN_LANGUAGE_COOKIE)?.value,
    cookieStore.get(READING_LANGUAGE_COOKIE)?.value,
    headerList.get("accept-language"),
  );
}

/** The language of the page's text where the route fixes it (proxy.ts), else none. */
async function fixedLanguage(): Promise<ReadingLanguage | null> {
  return cookieLanguage((await headers()).get(DOCUMENT_LANGUAGE_HEADER));
}

/** The language the server renders in; other pages correct <html lang> on hydration where they differ. */
function documentLanguage(request: RequestLanguage, fixed: ReadingLanguage | null) {
  return fixed ?? request.reading ?? request.chosen ?? request.browser;
}

export async function generateMetadata(): Promise<Metadata> {
  const language = documentLanguage(await readRequestLanguage(), await fixedLanguage());
  return { title: APP_TITLES[language], description: DESCRIPTIONS[language] };
}

export default async function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  const [request, fixed] = await Promise.all([readRequestLanguage(), fixedLanguage()]);
  return (
    <html lang={documentLanguage(request, fixed)} suppressHydrationWarning>
      <head>
        {/* Before first paint — see THEME_INIT_SCRIPT for why this is inline. */}
        <script dangerouslySetInnerHTML={{ __html: THEME_INIT_SCRIPT }} />
      </head>
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased`}
      >
        <RequestLanguageProvider value={request}>
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
        </RequestLanguageProvider>
      </body>
    </html>
  );
}
