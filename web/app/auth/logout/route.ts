import { NextResponse } from "next/server";
import { publicUrl } from "../../../auth/origin";
import { SESSION_COOKIE_NAME } from "../../../auth/session";

export async function POST() {
  const response = NextResponse.redirect(publicUrl("/login"), 303);
  response.cookies.set({
    name: SESSION_COOKIE_NAME,
    value: "",
    httpOnly: true,
    secure: true,
    sameSite: "lax",
    path: "/",
    maxAge: 0,
  });
  return response;
}
