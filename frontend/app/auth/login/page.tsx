"use client";
import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import Countdown from "../../components/Countdown";

// API base URL - change this to match your Flask server
const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL;

interface CycleStatus {
  status: string;
  cycle_number: number;
  survey_start_date: string;
  survey_end_date: string;
  processing_end_date: string;
  time_remaining: number; // Updated to match API
  next_phase: string;
  next_phase_date: string;
}

export default function Login() {
  const router = useRouter();
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
  const [cycleStatus, setCycleStatus] = useState<CycleStatus | null>(null);
  const [loadingCycle, setLoadingCycle] = useState(true);

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

    if (!formData.email) {
      newErrors.email = "Email is required";
      isValid = false;
    }

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
      //console.log("Sending login data:", formData);
      
      // Make request to the backend API
      const response = await fetch(`/api/auth/login`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Accept": "application/json"
        },
        body: JSON.stringify(formData)
      });
      
      const data = await response.json();
      console.log("Login response:", data);
      
      if (!response.ok) {
        // Extract the specific error message from the response if available
        const errorMsg = data.message || "Login failed. Please check your credentials.";
        throw new Error(errorMsg);
      }
      
      // Save email to localStorage for later use
      localStorage.setItem('userEmail', formData.email);
      
      setMessage("Login successful! Redirecting...");
      
      // Redirect to dashboard on successful login
      setTimeout(() => {
        router.push("/dashboard");
      }, 1000);
    } catch (error) {
      console.error("Login error:", error);
      setMessage(error instanceof Error ? error.message : String(error));
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
        <div className="signup-box">
          <h2 className="form-title">Login</h2>
          {message && <div className={`message ${message.includes("successful") ? "success" : "error"}`}>{message}</div>}
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
              {loading ? "Logging in..." : "Login"}
            </button>
          </form>
          <div className="signin-link">
            <strong>Don't have an account?</strong> <Link href="/">Sign up</Link>
          </div>
          <div className="signin-link" style={{ marginTop: '10px' }}>
            Forgot your password? <Link href="/auth/forgot-password">Click here</Link>
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
