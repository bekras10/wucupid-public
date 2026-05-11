import { NextResponse } from 'next/server';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL;


export async function POST() {
  console.log("Triggering match generation...");
  
  try {
    const response = await fetch(`${API_BASE_URL}/api/matches/generate`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({}),
    });
    
    if (!response.ok) {
      // Try to extract error message from response
      let errorMessage = 'Failed to generate matches';
      try {
        const errorData = await response.json();
        errorMessage = errorData.message || errorMessage;
      } catch (e) {
        // If can't parse error as JSON, use status text
        errorMessage = `${response.status}: ${response.statusText || errorMessage}`;
      }
      
      console.error(`Error generating matches: ${errorMessage}`);
      return NextResponse.json({ message: errorMessage }, { status: response.status });
    }
    
    const data = await response.json();
    console.log("Match generation successful:", data);
    return NextResponse.json(data);
  } catch (error) {
    console.error("Error during match generation:", error);
    const errorMessage = error instanceof Error ? error.message : 'An unexpected error occurred';
    return NextResponse.json(
      { message: `Failed to generate matches: ${errorMessage}` }, 
      { status: 500 }
    );
  }
} 