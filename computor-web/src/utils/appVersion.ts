// Baked at build time by computor.sh (docker/web/Dockerfile GIT_COMMIT arg);
// unset in `next dev`, where the generic fallback is shown instead.
export const APP_VERSION = process.env.NEXT_PUBLIC_GIT_COMMIT
  ? process.env.NEXT_PUBLIC_GIT_COMMIT.slice(0, 7)
  : 'dev';
