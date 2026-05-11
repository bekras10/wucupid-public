import { NextResponse } from 'next/server';
const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL;

export async function GET(request: Request) {
  try {
    // Get email from query string
    const url = new URL(request.url);
    const email = url.searchParams.get('email');
    
    if (!email) {
      return NextResponse.json(
        { message: 'Email parameter is required' },
        { status: 400 }
      );
    }
    
    console.log(`Fetching matches for email: ${email}`);
    
    // Call backend to get matches
    const response = await fetch(`${API_BASE_URL}/api/matches/get_by_email?email=${encodeURIComponent(email)}`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      }
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
    console.error('Error fetching matches:', error);
    return NextResponse.json(
      { message: error.message || 'An error occurred while fetching matches' },
      { status: 500 }
    );
  }
} 