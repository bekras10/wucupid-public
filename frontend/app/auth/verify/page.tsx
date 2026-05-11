"use client";
import { useEffect, useState, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";

function VerifyEmailContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [status, setStatus] = useState("Verifying your email...");
  const [error, setError] = useState(false);

  useEffect(() => {
    const verifyEmail = async () => {
      const token = searchParams.get("token");
      
      if (!token) {
        setStatus("Invalid verification link. No token provided.");
        setError(true);
        return;
      }

      try {
        const response = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/api/auth/verify/${token}`, {
          method: "POST",
          headers: { 'Accept': 'application/json' },
          // No body needed; token is in URL
          credentials: 'omit'
        });

        const contentType = response.headers.get('content-type') || '';
        let data: any = {};
        if (contentType.includes('application/json')) {
          data = await response.json();
        } else {
          const text = await response.text();
          try {
            data = JSON.parse(text);
          } catch {
            throw new Error(text || 'Unexpected response from server');
          }
        }

        if (!response.ok || data?.verified === false) {
          throw new Error(data?.message || "Verification failed");
        }

        setStatus("Email verified successfully! Redirecting to home page...");
        
        // Redirect to home page with success parameter after successful verification
        setTimeout(() => {
          console.log("Redirecting to /?verified=true");
          router.push("/?verified=true");
        }, 2000);
      } catch (error: any) {
        setStatus(error?.message || "Verification failed. Please try again.");
        setError(true);
      }
    };

    verifyEmail();
  }, [router, searchParams]);

  return (
    <div className="verify-box">
      <h2 className="form-title">Email Verification</h2>
      <div className={`message ${error ? "error" : "success"}`}>
        {status}
      </div>
    </div>
  );
}

export default function VerifyEmail() {
  return (
    <div className="container">
      <header className="header">
        WUCUPID
      </header>
      <main>
        <Suspense fallback={<div className="verify-box">Loading verification...</div>}>
          <VerifyEmailContent />
        </Suspense>
      </main>
    </div>
  );
}
