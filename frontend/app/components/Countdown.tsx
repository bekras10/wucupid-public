"use client";
import React, { useState, useEffect } from 'react';

interface CountdownProps {
  targetDate: string;
  phase: string;
  timeRemaining?: number;
  label?: string;
  onComplete?: () => void;
}

const Countdown: React.FC<CountdownProps> = ({ 
  targetDate, 
  phase, 
  timeRemaining: initialTimeRemaining,
  label = "Countdown", 
  onComplete 
}) => {
  const [timeLeft, setTimeLeft] = useState<{
    days: number;
    hours: number;
    minutes: number;
    seconds: number;
  }>({
    days: 0,
    hours: 0,
    minutes: 0,
    seconds: 0
  });

  // Store the initial time when the component mounts or when initialTimeRemaining changes
  const initialTimeRef = React.useRef<{ time: number; timestamp: number; phase: string } | null>(null);

  // Use refs for timer callbacks to avoid React updates during render
  const onCompleteRef = React.useRef(onComplete);
  
  // Update the ref when onComplete changes
  useEffect(() => {
    onCompleteRef.current = onComplete;
  }, [onComplete]);

  // Update initialTimeRef when initialTimeRemaining or phase changes
  useEffect(() => {
    if (typeof initialTimeRemaining === 'number') {
      initialTimeRef.current = {
        time: initialTimeRemaining,
        timestamp: Date.now(),
        phase: phase
      };
    } else {
      initialTimeRef.current = null;
    }
  }, [initialTimeRemaining, phase]);
  
  useEffect(() => {
    const calculateTimeLeft = () => {
      let secondsLeft: number;
      
      // If we have no data yet, show zeros but don't trigger completion
      if (!initialTimeRef.current && !targetDate) {
        setTimeLeft({ days: 0, hours: 0, minutes: 0, seconds: 0 });
        return;
      }
      
      if (initialTimeRef.current) {
        // Only use stored time if phase matches
        if (initialTimeRef.current.phase === phase) {
          // Calculate elapsed time since we got initialTimeRemaining
          const elapsedSeconds = Math.floor((Date.now() - initialTimeRef.current.timestamp) / 1000);
          secondsLeft = Math.max(0, initialTimeRef.current.time - elapsedSeconds);
        } else {
          // Phase changed, fall back to target date
          const target = new Date(targetDate).getTime();
          const now = new Date().getTime();
          secondsLeft = Math.floor((target - now) / 1000);
        }
      } else {
        // Calculate from target date
        const target = new Date(targetDate).getTime();
        const now = new Date().getTime();
        secondsLeft = Math.floor((target - now) / 1000);
      }
      
      if (secondsLeft <= 0) {
        setTimeLeft({ days: 0, hours: 0, minutes: 0, seconds: 0 });
        const callback = onCompleteRef.current;
        if (callback) {
          setTimeout(() => callback(), 0);
        }
        return;
      }
      
      const days = Math.floor(secondsLeft / (60 * 60 * 24));
      const hours = Math.floor((secondsLeft % (60 * 60 * 24)) / (60 * 60));
      const minutes = Math.floor((secondsLeft % (60 * 60)) / 60);
      const seconds = Math.floor(secondsLeft % 60);
      
      setTimeLeft({ days, hours, minutes, seconds });
    };
    
    // Calculate immediately
    calculateTimeLeft();
    
    // Update every second
    const timer = setInterval(calculateTimeLeft, 1000);
    
    return () => clearInterval(timer);
  }, [targetDate, phase, initialTimeRef.current]);
  
  const getMessage = () => {
    if (phase === 'survey_open') {
      return "Survey period ends in:";
    } else if (phase === 'processing') {
      return "Matches will be available in:";
    } else if (phase === 'matches_available') {
      return "Current matches available for:";
    } else if (phase === 'next_cycle_ends' || phase === 'new_cycle') {
      return "Next matching cycle begins in:";
    }
    return label;
  };
  
  // Don't render anything if we have no data
  if (!initialTimeRef.current && !targetDate) {
    return null;
  }
  
  return (
    <div className="countdown-container">
      <div className="countdown-message">{getMessage()}</div>
      <div className="countdown-timer">
        <div className="countdown-unit">
          <span className="countdown-value">{timeLeft.days}</span>
          <span className="countdown-label">Days</span>
        </div>
        <div className="countdown-unit">
          <span className="countdown-value">{timeLeft.hours}</span>
          <span className="countdown-label">Hours</span>
        </div>
        <div className="countdown-unit">
          <span className="countdown-value">{timeLeft.minutes}</span>
          <span className="countdown-label">Minutes</span>
        </div>
        <div className="countdown-unit">
          <span className="countdown-value">{timeLeft.seconds}</span>
          <span className="countdown-label">Seconds</span>
        </div>
      </div>
    </div>
  );
};

export default Countdown; 