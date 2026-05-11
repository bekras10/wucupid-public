"use client";
import { useState, useEffect, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";

function ResetPasswordContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [formData, setFormData] = useState({
    password: "",
    confirmPassword: ""
  });
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");
  const [token, setToken] = useState("");
  const [success, setSuccess] = useState(false);

  useEffect(() => {
    const tokenParam = searchParams.get("token");
    if (!tokenParam) {
      setMessage("Invalid reset link. No token provided.");
      return;
    }
    setToken(tokenParam);
  }, [searchParams]);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!formData.password || !formData.confirmPassword) {
      setMessage("Please fill in both password fields");
      return;
    }
    
    if (formData.password !== formData.confirmPassword) {
      setMessage("Passwords do not match");
      return;
    }
    
    if (formData.password.length < 8) {
      setMessage("Password must be at least 8 characters long");
      return;
    }
    
    setLoading(true);
    setMessage("");
    
    try {
      const response = await fetch(`/api/auth/reset-password`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Accept": "application/json"
        },
        body: JSON.stringify({ 
          token: token,
          password: formData.password 
        })
      });
      
      const data = await response.json();
      
      if (!response.ok) {
        throw new Error(data.message || "Failed to reset password");
      }
      
      setMessage("Password successfully updated! Redirecting to login...");
      setSuccess(true);
      
      // Redirect to login after success
      setTimeout(() => {
        router.push("/auth/login");
      }, 2000);
    } catch (error) {
      setMessage(error.message);
      setSuccess(false);
    } finally {
      setLoading(false);
    }
  };

  if (!token && !message.includes("Invalid reset link")) {
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
            <h2 className="form-title">Loading...</h2>
          </div>
        </main>
      </div>
    );
  }

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
            Enter your new password below.
          </p>
          {message && <div className={`message ${success ? "success" : "error"}`}>{message}</div>}
          {!success && token && !message.includes("Invalid reset link") && (
            <form onSubmit={handleSubmit}>
              <div className="input-group">
                <input 
                  type="password" 
                  name="password"
                  placeholder="New password" 
                  value={formData.password}
                  onChange={handleChange}
                  required 
                />
              </div>
              
              <div className="input-group">
                <input 
                  type="password" 
                  name="confirmPassword"
                  placeholder="Confirm new password" 
                  value={formData.confirmPassword}
                  onChange={handleChange}
                  required 
                />
              </div>
              
              <button type="submit" disabled={loading}>
                {loading ? "Updating..." : "Update Password"}
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

export default function ResetPassword() {
  return (
    <Suspense fallback={<div>Loading...</div>}>
      <ResetPasswordContent />
    </Suspense>
  );
} 