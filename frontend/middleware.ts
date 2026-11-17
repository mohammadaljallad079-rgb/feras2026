import { NextResponse, type NextRequest } from "next/server";

/**
 * Send the bare root to the default locale, and remember a visitor's explicit
 * choice so a returning visitor lands in the language they picked.
 *
 * Only `/` is handled here; every other path is owned by a real route, so
 * middleware never masks a 404 or rewrites an API call.
 */
export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;
  if (pathname !== "/") return NextResponse.next();

  const remembered = request.cookies.get("site.locale")?.value;
  const locale = remembered === "en" || remembered === "ar" ? remembered : "ar";
  const url = request.nextUrl.clone();
  url.pathname = `/${locale}`;
  return NextResponse.redirect(url);
}

export const config = { matcher: "/" };
