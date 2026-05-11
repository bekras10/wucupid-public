"use client";
import { useState, useEffect, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import Countdown from "./components/Countdown";

interface CycleStatus {
  status: string;
  cycle_number: number;
  survey_start_date: string;
  survey_end_date: string;
  processing_end_date: string;
  time_remaining: number;
  next_phase: string;
  next_phase_date: string;
}

// API base URL - change this to match your Flask server
const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL;

function HomeContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const search = searchParams.toString(); // compute once per render
  
  // Debug logging
  console.log("render", searchParams.get("verified"));
  
  const [formData, setFormData] = useState({
    email: "",
    password: ""
  });
  const [errors, setErrors] = useState({
    email: "",
    password: ""
  });
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");
  const [showBanner, setShowBanner] = useState(false);
  const [cycleStatus, setCycleStatus] = useState<CycleStatus | null>(null);
  const [loadingCycle, setLoadingCycle] = useState(true);

  useEffect(() => {
    // Check for verification success parameter
    if (search.includes("verified=true")) {
      console.log("Setting banner to true");
      setShowBanner(true); // 1) show it
      
      // strip only once, NOT on every render
      window.history.replaceState({}, "", "/");
    }
  }, [search]); // fires exactly when ?verified=... changes

  useEffect(() => {
    // Fetch cycle status
    fetchCycleStatus();
    
    // Set up interval to refresh cycle status
    const intervalId = setInterval(fetchCycleStatus, 60000);
    
    // Clean up on unmount
    return () => clearInterval(intervalId);
  }, []);

  const fetchCycleStatus = async () => {
    setLoadingCycle(true);
    try {
      console.log('Fetching cycle status from:', `/api/cycle/status`);
      
      const response = await fetch(`/api/cycle/status`, {
        method: 'GET',
        headers: {
          'Accept': 'application/json',
          'Content-Type': 'application/json',
        }
      });
      
      if (response.ok) {
        const data = await response.json();
        console.log('Cycle status data:', data);
        setCycleStatus(data);
      } else {
        console.error(`Failed to fetch cycle status: ${response.status} ${response.statusText}`);
      }
    } catch (error) {
      console.error("Error fetching cycle status:", error);
    } finally {
      setLoadingCycle(false);
    }
  };

  const validateForm = () => {
    const newErrors = {
      email: "",
      password: ""
    };
    let isValid = true;

    // Email validation (keep minimal validation on frontend)
    if (!formData.email) {
      newErrors.email = "Email is required";
      isValid = false;
    }

    // Password validation (keep minimal validation on frontend)
    if (!formData.password) {
      newErrors.password = "Password is required";
      isValid = false;
    }

    setErrors(newErrors);
    return isValid;
  };

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
    
    // Clear error when user starts typing
    if (errors[name]) {
      setErrors(prev => ({
        ...prev,
        [name]: ""
      }));
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!validateForm()) return;
    
    setLoading(true);
    setMessage("");
    
    try {
      const response = await fetch(`${API_BASE_URL}/api/auth/register`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Accept": "application/json"
        },
        body: JSON.stringify(formData)
      });
      
      const data = await response.json();
      
      if (!response.ok) {
        throw new Error(data.message || "Registration failed");
      }
      
      // For development mode, show verification link if provided
      if (data.verification_url) {
        setMessage(`Verification email would be sent! Use this link: ${data.verification_url}`);
      } else {
        setMessage(`Verification email sent! Please check your inbox. Emails may take a few minutes to arrive. If you don't receive an email within an hour, please contact us. By using WUCUPID, you agree to our <a href="/privacy-policy.html" target="_blank" rel="noopener noreferrer">Privacy Policy</a>.`);
      }
    } catch (error) {
      setMessage(error.message);
    } finally {
      setLoading(false);
    }
  };

  const formatStatusLabel = (status) => {
    switch (status) {
      case 'survey_open':
        return 'Survey Open';
      case 'processing':
        return 'Processing Matches';
      case 'matches_available':
        return 'Matches Available';
      default:
        return 'Unknown Status';
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
        {showBanner && (
          <div className="message success" style={{ marginBottom: '20px', maxWidth: '400px' }}>
            Email verified successfully!
          </div>
        )}
        <div className="signup-box">
          <h2 className="form-title">Register</h2>
          {message && (
            <div 
              className="message" 
              dangerouslySetInnerHTML={{
                __html: message.includes("Try logging in!") 
                  ? message.replace("Try logging in!", "<strong>Try logging in!</strong>")
                  : message
              }}
            />
          )}
          <form onSubmit={handleSubmit}>
            <div className={`input-group ${errors.email ? "error" : ""}`}>
              <input 
                type="email" 
                name="email"
                placeholder="WUSTL Email" 
                value={formData.email}
                onChange={handleChange}
                required 
              />
              {errors.email && <span className="error-text">{errors.email}</span>}
            </div>
            
            <div className={`input-group ${errors.password ? "error" : ""}`}>
              <input 
                type="password" 
                name="password"
                placeholder="Password" 
                value={formData.password}
                onChange={handleChange}
                required 
              />
              {errors.password && <span className="error-text">{errors.password}</span>}
            </div>
            
            <button type="submit" disabled={loading}>
              {loading ? "Signing up..." : "Sign Up"}
            </button>
          </form>
          <div className="signin-link">
            <strong>Already have an account?</strong> <Link href="/auth/login">Sign in</Link>
          </div>
        </div>

        {/* Cycle Status and Countdown */}
        {!loadingCycle && cycleStatus && (
          <div className="login-cycle-info">
            <div className={`cycle-status ${cycleStatus.status.replace('_', '-')}`}>
              Current Status: {formatStatusLabel(cycleStatus.status)}
            </div>
            <Countdown 
              targetDate={cycleStatus.next_phase_date}
              phase={cycleStatus.status}
              timeRemaining={cycleStatus.time_remaining}
              onComplete={fetchCycleStatus}
            />
          </div>
        )}
      </main>
    </div>
  );
}

export default function Home() {
  return (
    <Suspense fallback={<div className="container"><header className="header"><div className="logo-container has-logo-image"><img src="/images/logo.png" alt="WUCUPID Logo" className="logo-image" /><span className="logo-text">WUCUPID</span></div></header><main>Loading...</main></div>}>
      <HomeContent />
    </Suspense>
  );
}
