/** Build browser paths that remain inside an optional Next.js base path. */
const configuredBasePath = (process.env.NEXT_PUBLIC_BASE_PATH || '').trim().replace(/\/+$/, '');

export const APP_BASE_PATH = configuredBasePath;

export function appPath(path: string): string {
  const normalized = path.startsWith('/') ? path : `/${path}`;
  if (!APP_BASE_PATH) return normalized;
  if (normalized === '/') return `${APP_BASE_PATH}/`;
  return `${APP_BASE_PATH}${normalized}`;
}

/** Remove the optional deployment prefix before applying route-only checks. */
export function withoutAppBasePath(pathname: string): string {
  if (!APP_BASE_PATH) return pathname || '/';
  if (pathname === APP_BASE_PATH || pathname === `${APP_BASE_PATH}/`) return '/';
  if (pathname.startsWith(`${APP_BASE_PATH}/`)) {
    return pathname.slice(APP_BASE_PATH.length) || '/';
  }
  return pathname || '/';
}
