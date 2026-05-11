import { NextResponse } from 'next/server';
const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL;

export async function POST(request: Request) {
  try {
    const body = await request.json();
    
    // Avoid logging sensitive registration payloads (e.g., passwords)
    
    // Use relative path instead of hardcoded URL
    const response = await fetch(`${process.env.API_BASE_URL}/api/auth/register`, {
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
        // Try to parse as JSON if possible
        const errorJson = JSON.parse(errorText);
        return NextResponse.json(errorJson, { status: response.status });
      } catch {
        // Return as text if not JSON
        return NextResponse.json({ message: errorText || "Backend error" }, { status: response.status });
      }
    }
    
    const data = await response.json();
    console.log("Backend response:", data);
    return NextResponse.json(data);
    
  } catch (error) {
    console.error('Registration error:', error);
    return NextResponse.json(
      { message: error.message || 'An error occurred during registration' },
      { status: 500 }
    );
  }
} 