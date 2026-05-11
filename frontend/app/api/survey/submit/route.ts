import { NextResponse } from 'next/server';
const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL;


export async function POST(request: Request) {
  try {
    const body = await request.json();
    
    // Validate that we have answers
    if (!body.answers || Object.keys(body.answers).length === 0) {
      return NextResponse.json(
        { message: 'No survey answers provided' },
        { status: 400 }
      );
    }
    
    console.log('Frontend sending survey data to backend');
    
    // Call the backend API, forwarding cookies for auth
    const csrf = request.headers.get('x-csrf-token') || ''
    const response = await fetch(`${API_BASE_URL}/api/survey/submit`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        // Forward incoming cookies transparently
        'Cookie': request.headers.get('cookie') || '',
        'X-CSRF-Token': csrf,
      },
      body: JSON.stringify(body),
      redirect: 'manual',
    });
    
    if (!response.ok) {
      console.error(`Backend returned status: ${response.status}`);
      const errorText = await response.text();
      console.error("Backend error:", errorText);
      
      try {
        // Try to parse as JSON if possible
        const errorJson = JSON.parse(errorText);
        return NextResponse.json(errorJson, { status: response.status });
      } catch {
        // Return as text if not JSON
        return NextResponse.json({ message: errorText || "Backend error" }, { status: response.status });
      }
    }
    
    const text = await response.text();
    let data;
    try { data = text ? JSON.parse(text) : {}; } catch { data = { message: text || (response.ok ? 'OK' : 'Error') }; }
    return NextResponse.json(data, { status: response.status });
    
  } catch (error) {
    console.error('Error processing survey submission:', error);
    return NextResponse.json(
      { message: (error as Error)?.message || 'Failed to process survey submission' },
      { status: 500 }
    );
  }
} 