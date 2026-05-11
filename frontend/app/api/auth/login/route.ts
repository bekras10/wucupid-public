import { NextResponse } from 'next/server';
const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL;

export async function POST(request: Request) {
  try {
    const body = await request.json();

    // Forward to backend and preserve Set-Cookie so browser stores the session
    const response = await fetch(`${API_BASE_URL}/api/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
      redirect: 'manual',
    });

    const raw = await response.text();
    let data: any;
    try { data = raw ? JSON.parse(raw) : {}; } catch { data = { message: raw || (response.ok ? 'OK' : 'Error') }; }

    const next = NextResponse.json(data, { status: response.status });
    const setCookie = response.headers.get('set-cookie');
    if (setCookie) {
      next.headers.set('set-cookie', setCookie);
    }
    return next;
  } catch (error) {
    const message = error instanceof Error ? error.message : 'An error occurred during login';
    return NextResponse.json({ message }, { status: 500 });
  }
}