import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

const COOKIE_NAME = "genai_token";

export function middleware(req: NextRequest) {
  const authDisabled = process.env.NEXT_PUBLIC_AUTH_DISABLED === "1";
  if (authDisabled) return NextResponse.next();

  const { pathname } = req.nextUrl;
  if (pathname.startsWith("/login") || pathname.startsWith("/_next") || pathname.startsWith("/favicon")) {
    return NextResponse.next();
  }

  const token = req.cookies.get(COOKIE_NAME)?.value;
  if (!token) {
    const url = req.nextUrl.clone();
    url.pathname = "/login";
    return NextResponse.redirect(url);
  }
  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!api).*)"],
};
