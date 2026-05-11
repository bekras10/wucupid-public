import { NextResponse } from 'next/server';
const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL;


export async function GET() {
  try {
    console.log('Next.js API: Calling backend Flask server.');
    
    const response = await fetch(`${API_BASE_URL}/api/cycle/status`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
      // Adding a timeout of 10 seconds
      signal: AbortSignal.timeout(10000)
    });
    
    if (!response.ok) {
      let errorMessage = 'Failed to fetch cycle status';
      let errorDetails = '';
      
      try {
        const errorText = await response.text();
        console.error('Error response from backend:', errorText);
        
        try {
          // Try to parse as JSON
          const errorData = JSON.parse(errorText);
          errorMessage = errorData.message || errorData.error || errorMessage;
          errorDetails = JSON.stringify(errorData);
        } catch (parseError) {
          // If not JSON, use the text
          errorDetails = errorText;
        }
      } catch (e) {
        errorDetails = `${response.status}: ${response.statusText || errorMessage}`;
      }
      
      console.error(`Error fetching cycle status: ${errorMessage}`);
      console.error(`Details: ${errorDetails}`);
      
      return NextResponse.json({ 
        message: errorMessage,
        details: errorDetails,
        status: response.status
      }, { status: response.status });
    }
    
    const data = await response.json();
    return NextResponse.json(data);
    
  } catch (error) {
    console.error("Error fetching cycle status:", error);
    const errorMessage = error instanceof Error ? error.message : 'An unexpected error occurred';
    return NextResponse.json(
      { 
        message: `Failed to fetch cycle status: ${errorMessage}`,
        details: error instanceof Error ? (error.stack || '') : ''
      }, 
      { status: 500 }
    );
  }
} 