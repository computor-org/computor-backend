'use client';

import { useEffect, useState } from 'react';
import { useAuth } from '@/src/contexts/AuthContext';
import { API_BASE_URL, apiFetch } from '@/src/utils/apiClient';

type SocialProvider = 'google' | 'github' | 'gitlab';

const PROVIDERS: Array<{ name: SocialProvider; label: string }> = [
  { name: 'google', label: 'Google' },
  { name: 'github', label: 'GitHub' },
  { name: 'gitlab', label: 'GitLab' },
];

export default function SocialLoginButtons({ registration = false }: { registration?: boolean }) {
  const { loginWithSSO } = useAuth();
  const [enabled, setEnabled] = useState<SocialProvider[]>([]);

  useEffect(() => {
    apiFetch(`${API_BASE_URL}/auth/providers`)
      .then(async (response) => {
        if (!response.ok) return;
        const providers = (await response.json()) as Array<{ name: string; enabled: boolean }>;
        setEnabled(
          PROVIDERS.map((provider) => provider.name).filter((name) =>
            providers.some((provider) => provider.name === name && provider.enabled),
          ),
        );
      })
      .catch(() => setEnabled([]));
  }, []);

  if (enabled.length === 0) {
    return (
      <p className="text-center text-sm text-gray-600">
        No social registration provider is configured for this instance.
      </p>
    );
  }

  return (
    <div className="space-y-3" aria-label="Social sign-in providers">
      {enabled.map((provider) => {
        const metadata = PROVIDERS.find((item) => item.name === provider)!;
        return (
          <button
            key={provider}
            type="button"
            onClick={() => loginWithSSO(provider, registration)}
            className="relative flex w-full items-center justify-center rounded-lg border border-gray-300 bg-white px-4 py-2.5 text-sm font-medium text-gray-800 shadow-sm transition hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-1"
          >
            <ProviderLogo provider={provider} />
            <span>Continue with {metadata.label}</span>
          </button>
        );
      })}
    </div>
  );
}

function ProviderLogo({ provider }: { provider: SocialProvider }) {
  if (provider === 'google') {
    return (
      <svg className="absolute left-4 h-5 w-5" viewBox="0 0 24 24" aria-hidden="true">
        <path fill="#4285F4" d="M21.35 12.27c0-.7-.06-1.37-.18-2.02H12v3.82h5.24a4.48 4.48 0 0 1-1.94 2.94v2.45h3.14c1.84-1.69 2.91-4.18 2.91-7.19Z" />
        <path fill="#34A853" d="M12 21.6c2.63 0 4.84-.87 6.45-2.36l-3.14-2.45c-.87.58-1.98.93-3.31.93-2.54 0-4.69-1.72-5.46-4.03H3.3v2.53A9.74 9.74 0 0 0 12 21.6Z" />
        <path fill="#FBBC05" d="M6.54 13.69a5.86 5.86 0 0 1 0-3.38V7.78H3.3a9.6 9.6 0 0 0 0 8.44l3.24-2.53Z" />
        <path fill="#EA4335" d="M12 6.28c1.43 0 2.72.49 3.73 1.46l2.8-2.8C16.84 3.36 14.63 2.4 12 2.4a9.74 9.74 0 0 0-8.7 5.38l3.24 2.53C7.31 8 9.46 6.28 12 6.28Z" />
      </svg>
    );
  }

  if (provider === 'github') {
    return (
      <svg className="absolute left-4 h-5 w-5 text-gray-900" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
        <path d="M12 .5a12 12 0 0 0-3.79 23.39c.6.11.82-.26.82-.58v-2.25c-3.34.73-4.04-1.61-4.04-1.61-.55-1.39-1.34-1.76-1.34-1.76-1.09-.75.08-.74.08-.74 1.2.08 1.83 1.23 1.83 1.23 1.07 1.83 2.8 1.3 3.49.99.11-.77.42-1.3.76-1.6-2.67-.3-5.47-1.34-5.47-5.95 0-1.31.47-2.38 1.23-3.22-.12-.3-.53-1.52.12-3.18 0 0 1-.32 3.3 1.23a11.5 11.5 0 0 1 6 0c2.3-1.55 3.3-1.23 3.3-1.23.65 1.66.24 2.88.12 3.18.76.84 1.23 1.91 1.23 3.22 0 4.62-2.8 5.64-5.48 5.94.43.37.81 1.1.81 2.22v3.29c0 .32.22.69.83.57A12 12 0 0 0 12 .5Z" />
      </svg>
    );
  }

  return (
    <svg className="absolute left-4 h-5 w-5" viewBox="0 0 24 24" aria-hidden="true">
      <path fill="#FC6D26" d="m22.2 13.4-1.25-3.84-2.47-7.6c-.13-.4-.7-.4-.83 0l-2.47 7.6H8.82l-2.47-7.6c-.13-.4-.7-.4-.83 0l-2.47 7.6L1.8 13.4a.83.83 0 0 0 .3.93l9.9 7.2 9.9-7.2a.83.83 0 0 0 .3-.93Z" />
      <path fill="#E24329" d="m12 21.53 5.48-11.97H14.4L12 16.1l-2.4-6.54H6.52L12 21.53Z" />
      <path fill="#FCA326" d="M12 21.53 3.05 14.33a.83.83 0 0 1-.3-.93l1.25-3.84h4.1L12 21.53Z" />
    </svg>
  );
}
