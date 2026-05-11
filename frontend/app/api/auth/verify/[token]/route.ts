import { NextResponse } from 'next/server';

export const runtime = 'nodejs';

function getApiBaseUrl(): string | undefined {
  const base = process.env.API_BASE_URL || process.env.NEXT_PUBLIC_API_BASE_URL;
  if (!base) return undefined;
  return base.replace(/\/$/, '');
}

// Server-side base URL for the Flask API
const API_BASE_URL = process.env.API_BASE_URL;

export async function GET(
  _request: Request,
  context: any
) {
  try {
    const token = context?.params?.token?.trim();
    if (!token) {
      return NextResponse.json({ message: 'Verification token is required' }, { status: 400 });
    }

    const baseUrl = getApiBaseUrl();
    if (!baseUrl) {
      console.error('API_BASE_URL is not configured');
      return NextResponse.json({ message: 'Server misconfiguration' }, { status: 500 });
    }

    // Prevent accidental recursion if base URL points to this same origin
    const reqOrigin = new URL(_request.url).origin;
    if (baseUrl.startsWith(reqOrigin)) {
      console.error('API_BASE_URL points to frontend origin; refusing to recurse');
      return NextResponse.json({ message: 'Server misconfiguration' }, { status: 500 });
    }

    const backendUrl = `${baseUrl}/api/auth/verify/${encodeURIComponent(token)}`;

    // Forward to backend as POST (backend only verifies on POST)
    const response = await fetch(backendUrl, {
      method: 'POST',
      headers: {
        'Accept': 'application/json'
      }
    });

    const text = await response.text();
    let payload: any = { message: text };
    try {
      payload = JSON.parse(text);
    } catch {
      // leave as text payload
    }

    return NextResponse.json(payload, { status: response.status });
  } catch (error: any) {
    console.error('Verify proxy error:', error);
    return NextResponse.json(
      { message: error?.message || 'Verification failed' },
      { status: 500 }
    );
  }
}

// Optional: Support POST in case clients use it directly
export async function POST(
  _request: Request,
  context: any
) {
  try {
    const token = context?.params?.token?.trim();
    if (!token) {
      return NextResponse.json({ message: 'Verification token is required' }, { status: 400 });
    }

    const baseUrl = getApiBaseUrl();
    if (!baseUrl) {
      console.error('API_BASE_URL is not configured');
      return NextResponse.json({ message: 'Server misconfiguration' }, { status: 500 });
    }

    const reqOrigin = new URL(_request.url).origin;
    if (baseUrl.startsWith(reqOrigin)) {
      console.error('API_BASE_URL points to frontend origin; refusing to recurse');
      return NextResponse.json({ message: 'Server misconfiguration' }, { status: 500 });
    }

    const backendUrl = `${baseUrl}/api/auth/verify/${encodeURIComponent(token)}`;

    const response = await fetch(backendUrl, {
      method: 'POST',
      headers: {
        'Accept': 'application/json'
      }
    });

    const text = await response.text();
    let payload: any = { message: text };
    try {
      payload = JSON.parse(text);
    } catch {
      // leave as text payload
    }

    return NextResponse.json(payload, { status: response.status });
  } catch (error: any) {
    console.error('Verify proxy error:', error);
    return NextResponse.json(
      { message: error?.message || 'Verification failed' },
      { status: 500 }
    );
  }
}


