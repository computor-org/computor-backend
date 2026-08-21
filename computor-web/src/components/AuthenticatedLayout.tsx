'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/src/contexts/AuthContext';
import { CourseProvider } from '@/src/contexts/CourseContext';
import Sidebar from './Sidebar';
import TopBar from './TopBar';
import MaintenanceBanner from './MaintenanceBanner';
import { API_BASE_URL, apiGet, redirectToConsent } from '@/src/utils/apiClient';
import type { ConsentStatusGet as ConsentStatus } from 'types/generated';

// Consent bootstrap check runs once per authenticated session per page load;
// mid-session changes (withdrawal, policy version bump) are caught by the 403
// consent_required interceptor in apiClient. Reset on logout so a different
// user signing in without a full reload is checked again.
let consentChecked = false;

export default function AuthenticatedLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const { isAuthenticated, isLoading } = useAuth();

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      consentChecked = false;
      router.push('/login');
    }
  }, [isAuthenticated, isLoading, router]);

  useEffect(() => {
    if (isLoading || !isAuthenticated || consentChecked) return;
    consentChecked = true;
    apiGet(`${API_BASE_URL}/consent/status`)
      .then(async (response) => {
        if (!response.ok) return;
        const status: ConsentStatus = await response.json();
        if (status.required_version && !status.has_consented) {
          redirectToConsent();
        }
      })
      .catch(() => {
        // Best-effort: the consent interceptor gates on the next API call anyway.
      });
  }, [isAuthenticated, isLoading]);

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-canvas">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-accent mx-auto"></div>
          <p className="mt-4 text-muted">Loading...</p>
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return null;
  }

  return (
    // CourseProvider wraps the chrome, not just the page: the top bar shows the
    // course name too, and it used to fetch the course a second time to get it.
    <CourseProvider>
    <div className="h-screen overflow-hidden bg-canvas flex">
      {/* Sidebar (fixed; scrolls internally via its own nav) */}
      <Sidebar />

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* Top Bar */}
        <TopBar />
        <MaintenanceBanner />

        {/*
          Page content. Padding deliberately lives on the page scaffold
          (ListPageLayout), not here: the scaffold — not <main> — is the element
          that owns the relationship between the fixed PageHeader, the scrolling
          body and any pinned footer, and PageHeader has no padding of its own,
          so it must share the scaffold's. Padding here would sit outside the
          real scroll container and double up with the scaffold's.
        */}
        <main className="flex-1 overflow-y-auto min-h-0 scroll-slim">
          {children}
        </main>
      </div>
    </div>
    </CourseProvider>
  );
}
