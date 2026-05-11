import { NextResponse } from 'next/server';
const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL;

export async function POST(request: Request) {
  try {
    const body = await request.json();
    
    // Validate that we have email
    if (!body.email) {
      return NextResponse.json(
        { message: 'Email is required' },
        { status: 400 }
      );
    }
    
    console.log('Frontend saving survey progress to backend:', body);
    
    // Call the backend API
    const response = await fetch(`${API_BASE_URL}/api/survey/progress`, {
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
    console.error('Error saving survey progress:', error);
    return NextResponse.json(
      { message: error.message || 'Failed to save survey progress' },
      { status: 500 }
    );
  }
}

export async function GET(request: Request) {
  try {
    const { searchParams } = new URL(request.url);
    const email = searchParams.get('email');
    
    if (!email) {
      return NextResponse.json(
        { message: 'Email is required', hasProgress: false },
        { status: 400 }
      );
    }
    
    console.log('Frontend fetching survey progress from backend for:', email);
    
    // Call the backend API
    const response = await fetch(`${API_BASE_URL}/api/survey/progress?email=${encodeURIComponent(email)}`, {
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
        return NextResponse.json({ message: errorText || "Backend error", hasProgress: false }, { status: response.status });
      }
    }
    
    const data = await response.json();
    console.log("Backend response:", data);
    return NextResponse.json(data);
    
  } catch (error) {
    console.error('Error fetching survey progress:', error);
    return NextResponse.json(
      { message: error.message || 'Failed to fetch survey progress', hasProgress: false },
      { status: 500 }
    );
  }
} 