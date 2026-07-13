import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Enable standalone output for Docker
  // This creates a minimal production build in .next/standalone
  output: 'standalone',

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
