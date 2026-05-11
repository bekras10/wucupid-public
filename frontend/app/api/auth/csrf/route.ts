import { NextResponse } from 'next/server';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL;

export async function GET() {
  try {
    const res = await fetch(`${API_BASE_URL}/api/auth/csrf`, {
      method: 'GET',
      headers: { 'Accept': 'application/json' },
      redirect: 'manual',
    });
    const bodyText = await res.text();
    let data: any;
    try { data = bodyText ? JSON.parse(bodyText) : {}; } catch { data = { message: bodyText || (res.ok ? 'OK' : 'Error') }; }
    const next = NextResponse.json(data, { status: res.status });
    const setCookie = res.headers.get('set-cookie');
    if (setCookie) next.headers.set('set-cookie', setCookie);
    return next;
  } catch (e: any) {
    return NextResponse.json({ message: e?.message || 'CSRF setup failed' }, { status: 500 });
  }
}


