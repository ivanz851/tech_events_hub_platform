import { NextResponse } from "next/server";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8080";

export async function GET() {
  return NextResponse.redirect(`${API_URL}/auth/yandex/login`);
}
