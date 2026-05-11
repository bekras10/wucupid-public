// Simple client-side helpers for CSRF

export function getCookie(name: string): string {
  if (typeof document === 'undefined') return '';
  const match = document.cookie
    .split('; ')
    .find((c) => c.startsWith(name + '='));
  return match ? decodeURIComponent(match.split('=')[1]) : '';
}

export function getCsrfToken(): string {
  return getCookie('csrf_token');
}

export async function ensureCsrfCookie(): Promise<void> {
  try {
    // Hitting this route causes the server to set the csrf_token cookie
    await fetch('/api/auth/csrf', { method: 'GET', credentials: 'include' });
  } catch {
    // Best-effort; failures will be retried on next request
  }
}


