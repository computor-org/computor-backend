'use client';

import { useState, useRef, useEffect } from 'react';
import Link from 'next/link';

interface RegistrationMethod {
  label: string;
  description?: string;
  href: string;
}

// Add new self-service registration methods here as they become available.
const REGISTRATION_METHODS: RegistrationMethod[] = [
  {
    label: 'GitLab Personal Access Token',
    description: 'Verify your identity with a GitLab PAT',
    href: '/register/gitlab',
  },
];

export default function SetupLoginMenu() {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  return (
    <div className="relative" ref={ref}>
      <button
        type="button"
        onClick={() => setOpen(o => !o)}
        className="px-4 py-2 text-blue-600 hover:text-blue-700 transition-colors font-medium flex items-center gap-1"
      >
        Set up login
        <svg
          className={`h-4 w-4 transition-transform ${open ? 'rotate-180' : ''}`}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {open && (
        <div className="absolute right-0 mt-2 w-72 bg-white rounded-lg shadow-lg border border-gray-200 py-2 z-50">
          <div className="px-3 pb-1 text-xs font-medium text-gray-400 uppercase tracking-wide">
            Choose a method
          </div>
          {REGISTRATION_METHODS.map(method => (
            <Link
              key={method.href}
              href={method.href}
              onClick={() => setOpen(false)}
              className="block px-3 py-2 hover:bg-gray-50 transition-colors"
            >
              <div className="text-sm font-medium text-gray-900">{method.label}</div>
              {method.description && (
                <div className="text-xs text-gray-500">{method.description}</div>
              )}
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
