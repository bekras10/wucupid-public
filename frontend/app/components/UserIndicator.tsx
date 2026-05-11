"use client";
import { useState, useEffect } from 'react';
import { usePathname } from 'next/navigation';

export default function UserIndicator() {
  const [userEmail, setUserEmail] = useState<string | null>(null);
  const [isVisible, setIsVisible] = useState(false);
  const pathname = usePathname();

  useEffect(() => {
    // Check if user is logged in by looking for email in localStorage
    const checkUserStatus = () => {
      if (typeof window !== 'undefined') {
        const email = localStorage.getItem('userEmail');
        setUserEmail(email);
        // Only show on dashboard-related pages when user is logged in
        const isDashboardPage = pathname.startsWith('/dashboard') || pathname.startsWith('/survey') || pathname.startsWith('/matches');
        setIsVisible(!!email && isDashboardPage);
      }
    };

    // Check immediately
    checkUserStatus();

    // Set up an interval to check periodically in case user logs in/out
    const interval = setInterval(checkUserStatus, 1000);

    // Also listen for storage changes (in case user logs out in another tab)
    const handleStorageChange = (e: StorageEvent) => {
      if (e.key === 'userEmail') {
        checkUserStatus();
      }
    };

    window.addEventListener('storage', handleStorageChange);

    return () => {
      clearInterval(interval);
      window.removeEventListener('storage', handleStorageChange);
    };
  }, [pathname]);

  const handleLogout = () => {
    localStorage.removeItem('userEmail');
    localStorage.removeItem('surveyCompleted');
    setUserEmail(null);
    setIsVisible(false);
    // Redirect to home page
    window.location.href = '/';
  };

  if (!isVisible || !userEmail) {
    return null;
  }

  return (
    <div className="user-indicator">
      <div className="user-indicator-content">
        <div className="user-email">Logged in as:</div>
        <div className="user-email-address">{userEmail}</div>
        <div className="user-indicator-actions">
          <button onClick={handleLogout} className="logout-link">
            Logout
          </button>
        </div>
      </div>
    </div>
  );
} 