import { NextResponse } from 'next/server';
const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL;

export async function GET(request: Request) {
  try {
    const { searchParams } = new URL(request.url);
    const email = searchParams.get('email');
    
    if (!email) {
      return NextResponse.json(
        { message: 'Email is required', hasCompletedSurvey: false },
        { status: 400 }
      );
    }
    
    console.log('Frontend checking survey status from backend for:', email);
    
    // Call the backend API
    const response = await fetch(`${API_BASE_URL}/api/survey/check?email=${encodeURIComponent(email)}`, {
      method: 'GET',
      headers: {
        'Accept': 'application/json',
      },
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
        return NextResponse.json({ message: errorText || "Backend error", hasCompletedSurvey: false }, { status: response.status });
      }
    }
    
    const data = await response.json();
    console.log("Backend response:", data);
    return NextResponse.json(data);
    
  } catch (error) {
    console.error('Error checking survey status:', error);
    return NextResponse.json(
      { message: error.message || 'Failed to check survey status', hasCompletedSurvey: false },
      { status: 500 }
    );
  }
} 