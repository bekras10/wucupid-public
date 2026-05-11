"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";

export default function ForgotPassword() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");
  const [success, setSuccess] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!email) {
      setMessage("Please enter your email address");
      return;
    }
    
    setLoading(true);
    setMessage("");
    
    try {
      const response = await fetch(`/api/auth/forgot-password`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Accept": "application/json"
        },
        body: JSON.stringify({ email })
      });
      
      const data = await response.json();
      
      if (!response.ok) {
        throw new Error(data.message || "Failed to send password reset email");
      }
      
      setMessage("Password reset email successfully sent! Please check your inbox.");
      setSuccess(true);
    } catch (error) {
      setMessage(error.message);
      setSuccess(false);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="container">
      <header className="header">
        <div className="logo-container has-logo-image">
          <img src="/images/logo.png" alt="WUCUPID Logo" className="logo-image" />
          <span className="logo-text">WUCUPID</span>
        </div>
      </header>
      <main>
        <div className="signup-box">
          <h2 className="form-title">Reset Password</h2>
          <p style={{ marginBottom: '20px', color: '#666', textAlign: 'center', fontSize: '0.9rem' }}>
            Enter your email address and we'll send you a link to reset your password.
          </p>
          {message && <div className={`message ${success ? "success" : "error"}`}>{message}</div>}
          {!success && (
            <form onSubmit={handleSubmit}>
              <div className="input-group">
                <input 
                  type="email" 
                  name="email"
                  placeholder="Enter your WUSTL email" 
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required 
                />
              </div>
              
              <button type="submit" disabled={loading}>
                {loading ? "Sending..." : "Send Reset Email"}
              </button>
            </form>
          )}
          <div className="signin-link">
            Remember your password? <Link href="/auth/login">Back to login</Link>
          </div>
        </div>
      </main>
    </div>
  );
} 