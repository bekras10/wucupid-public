import { NextResponse } from 'next/server';
const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL;

export async function POST(request: Request) {
  try {
    const body = await request.json();
    
    // Avoid logging sensitive flows
    
    const response = await fetch(`${API_BASE_URL}/api/auth/reset-password`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(body),
    });
    
    if (!response.ok) {
      console.error(`Backend returned status: ${response.status}`);
      const errorText = await response.text();
      console.error("Backend error:", errorText);
      
      try {
        const errorJson = JSON.parse(errorText);
        return NextResponse.json(errorJson, { status: response.status });
      } catch {
        return NextResponse.json({ message: errorText || "Backend error" }, { status: response.status });
      }
    }
    
    const data = await response.json();
    console.log("Backend reset password response:", data);
    return NextResponse.json(data);
    
  } catch (error) {
    console.error('Reset password error:', error);
    return NextResponse.json(
      { message: error instanceof Error ? error.message : 'An error occurred during password reset' },
      { status: 500 }
    );
  }
} 