const COOKIE_NAME = "genai_token";

export function getToken(): string | null {
  if (typeof document === "undefined") return null;
  const m = document.cookie.match(new RegExp(`(?:^|; )${COOKIE_NAME}=([^;]*)`));
  return m ? decodeURIComponent(m[1]) : null;
}

export function setToken(token: string) {
  if (typeof document === "undefined") return;
  const value = encodeURIComponent(token.trim());
  // 30 days
  document.cookie = `${COOKIE_NAME}=${value}; Path=/; Max-Age=${30 * 24 * 60 * 60}`;
}

export function clearToken() {
  if (typeof document === "undefined") return;
  document.cookie = `${COOKIE_NAME}=; Path=/; Max-Age=0`;
}
