import type { NextConfig } from "next";

// Next.js applies basePath to Link/router URLs and emitted asset URLs at build
// time. Production leaves it empty; path-routed previews set it to
// /preview/<id> so a preview can share code.tugraz.at without leaking requests
// to the production root.
const basePath = (process.env.NEXT_PUBLIC_BASE_PATH || '').trim().replace(/\/+$/, '') || undefined;

const nextConfig: NextConfig = {
  // Enable standalone output for Docker
  // This creates a minimal production build in .next/standalone
  output: 'standalone',
  basePath,

  // Optionally disable source maps in production for smaller bundle
  // productionBrowserSourceMaps: false,

  async redirects() {
    // Legacy top-level dashboard paths. Student/lecturer/tutor actions are
    // always course-scoped (the real views live at /courses/[id]/...), so
    // these send users to the course picker. Server-side redirects replacing
    // the former ~21-line client-side router.replace() stub pages (TASK-411).
    const toCourses = (source: string) => ({
      source,
      destination: '/courses',
      permanent: false,
    });
    return [
      toCourses('/student'),
      toCourses('/student/courses'),
      toCourses('/student/assignments'),
      toCourses('/lecturer'),
      toCourses('/lecturer/courses'),
      toCourses('/tutor'),
      toCourses('/tutor/students'),
      toCourses('/assignments'),
    ];
  },
};

export default nextConfig;
