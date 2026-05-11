"use client";
import React, { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import Countdown from '../components/Countdown';

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

export default function Dashboard() {
  const router = useRouter();
  const [activeTab, setActiveTab] = useState('survey');
  const [hasCompletedSurvey, setHasCompletedSurvey] = useState(false);
  const [hasSurveyProgress, setHasSurveyProgress] = useState(false);
  const [loading, setLoading] = useState(true);
  const [matches, setMatches] = useState([]);
  const [loadingMatches, setLoadingMatches] = useState(false);
  const [matchError, setMatchError] = useState('');
  const [userEmail, setUserEmail] = useState('');
  const [isAdmin, setIsAdmin] = useState(false);
  const [cycleStatus, setCycleStatus] = useState<CycleStatus | null>(null);
  const [loadingCycle, setLoadingCycle] = useState(true);

  useEffect(() => {
    // Load cycle status
    fetchCycleStatus();

    // Check if user has completed survey and has progress
    const checkSurveyStatus = async () => {
      setLoading(true);
      try {
        const email = localStorage.getItem('userEmail');
        if (!email) {
          setLoading(false);
          return;
        }

        setUserEmail(email);
        setIsAdmin(email === 'admin@wustl.edu');

        // Call backend to check if user has completed survey
        const response = await fetch(`/api/survey/check?email=${encodeURIComponent(email)}`, {
          method: 'GET',
          mode: 'cors',
          headers: {
            'Accept': 'application/json'
          }
        });

        if (response.ok) {
          const data = await response.json();
          setHasCompletedSurvey(data.hasCompletedSurvey);
          
          // If survey is completed, fetch matches
          if (data.hasCompletedSurvey) {
            fetchMatches(email);
          } else {
            // Check for saved progress if survey not completed
            try {
              const progressResponse = await fetch(`/api/survey/progress?email=${encodeURIComponent(email)}`);
              if (progressResponse.ok) {
                const progressData = await progressResponse.json();
                setHasSurveyProgress(progressData.hasProgress);
              }
            } catch (error) {
              console.error("Error checking survey progress:", error);
              // Fallback to checking localStorage
              const savedState = localStorage.getItem('surveyState');
              setHasSurveyProgress(!!savedState);
            }
          }
        }
      } catch (error) {
        console.error("Error checking survey status:", error);
        // If API fails, check localStorage as fallback
        const completionFlag = localStorage.getItem('surveyCompleted');
        setHasCompletedSurvey(completionFlag === 'true');
        
        // Check for progress
        const savedState = localStorage.getItem('surveyState');
        setHasSurveyProgress(!!savedState);
        
        // If survey is completed, fetch matches
        if (completionFlag === 'true') {
          const email = localStorage.getItem('userEmail');
          if (email) {
            fetchMatches(email);
          }
        }
      } finally {
        setLoading(false);
      }
    };

    checkSurveyStatus();

    // Set up interval to refresh cycle status - every 30 seconds is enough
    const intervalId = setInterval(fetchCycleStatus, 30000);
    
    return () => clearInterval(intervalId);
  }, []);

  // Create a callback reference for countdown completion
  const handleCountdownComplete = useCallback(() => {
    console.log('Countdown completed, refreshing cycle status');
    // Add a small delay to avoid race conditions
    setTimeout(fetchCycleStatus, 1000);
  }, []);

  const fetchCycleStatus = async () => {
    // Don't set loading if we already have cycle data (to avoid flickering)
    if (!cycleStatus) {
      setLoadingCycle(true);
    }
    
    try {
      console.log('Fetching cycle status...');
      const response = await fetch(`/api/cycle/status`, {
        method: 'GET',
        mode: 'cors',
        headers: {
          'Accept': 'application/json',
          'Content-Type': 'application/json',
        }
      });
      
      if (response.ok) {
        const data = await response.json();
        console.log('Cycle status data:', data);
        
        // Check if we transitioned to matches_available phase
        if (data.status === 'matches_available' && 
            (cycleStatus === null || cycleStatus.status !== 'matches_available')) {
          console.log('Matches are now available, refreshing matches');
          const email = localStorage.getItem('userEmail');
          if (email && hasCompletedSurvey) {
            fetchMatches(email);
          }
        }
        
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

  const fetchMatches = async (email) => {
    setLoadingMatches(true);
    setMatchError('');
    try {
      const response = await fetch(`/api/matches/get?email=${encodeURIComponent(email)}`, {
        method: 'GET',
        mode: 'cors',
        headers: {
          'Accept': 'application/json'
        }
      });
      
      if (response.ok) {
        const data = await response.json();
        setMatches(data.matches || []);
        if (data.message && !data.matches?.length) {
          setMatchError(data.message);
        }
      } else {
        const errorData = await response.json();
        setMatchError(errorData.message || 'Failed to fetch matches');
      }
    } catch (error) {
      console.error('Error fetching matches:', error);
      setMatchError('An error occurred while fetching matches');
    } finally {
      setLoadingMatches(false);
    }
  };

  const handleTabChange = (tab) => {
    setActiveTab(tab);
  };

  const startSurvey = () => {
    if (hasSurveyProgress) {
      // Continue from where they left off
      router.push('/survey');
    } else {
      // Start fresh
      router.push('/survey?start=true');
    }
  };

  // Format the match score as a percentage
  const formatMatchScore = (score) => {
    return `${Math.round(score * 100)}%`;
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

  const getStatusClass = (status) => {
    switch (status) {
      case 'survey_open':
        return 'survey-open';
      case 'processing':
        return 'processing';
      case 'matches_available':
        return 'matches-available';
      default:
        return '';
    }
  };

  return (
    <div className="dashboard-container">
      <header className="dashboard-header">
      <div className="logo-container has-logo-image">
        <img src="/images/logo.png" alt="WUCUPID Logo" className="logo-image" />
        <span className="logo-text">WUCUPID</span>
      </div>
      </header>
      
      <main className="dashboard">
        {/* Cycle Status and Countdown */}
        {!loadingCycle && cycleStatus && (
          <div className="cycle-info">
            <div className={`cycle-status ${getStatusClass(cycleStatus.status)}`}>
              Current Status: {formatStatusLabel(cycleStatus.status)}
            </div>
            <Countdown 
              targetDate={cycleStatus.next_phase_date}
              phase={cycleStatus.status}
              timeRemaining={cycleStatus.time_remaining}
              onComplete={handleCountdownComplete}
            />

          </div>
        )}
      
        <div className="tabs-container">
          <div className="tabs">
            <button 
              className={`tab ${activeTab === 'survey' ? 'active' : ''}`}
              onClick={() => handleTabChange('survey')}
            >
              Take the Survey
            </button>
            <button 
              className={`tab ${activeTab === 'matches' ? 'active' : ''}`}
              onClick={() => handleTabChange('matches')}
            >
              Your Matches
            </button>
            <button 
              className={`tab ${activeTab === 'about' ? 'active' : ''}`}
              onClick={() => handleTabChange('about')}
            >
              About Us
            </button>
          </div>
          
          <div className="tab-content">
            {activeTab === 'survey' && (
              <div className="survey-tab">
                <h2>Take the Matching Survey</h2>
                {loading ? (
                  <p>Loading survey status...</p>
                ) : hasCompletedSurvey ? (
                  <div>
                    <p>You've already completed the survey! Your responses have been saved.</p>
                    <p>Check the "Your Matches" tab to see potential matches once they're available.</p>
                  </div>
                ) : !cycleStatus ? (
                  <p>Unable to determine survey availability. Please try again later.</p>
                ) : cycleStatus.status === 'survey_open' ? (
                  <>
                    {hasSurveyProgress ? (
                      <>
                        <p>Continue where you left off in the survey to find your perfect match!</p>
                        <button className="primary-button" onClick={startSurvey}>Continue Survey</button>
                      </>
                    ) : (
                      <>
                        <p>Complete the survey to find your perfect match!</p>
                        <button className="primary-button" onClick={startSurvey}>Start Survey</button>
                      </>
                    )}
                  </>
                ) : (
                  <div>
                    <p>The survey period has ended. The next survey period will begin after matches are released.</p>
                    <p>Please check back when the next survey period begins!</p>
                  </div>
                )}
              </div>
            )}
            
            {activeTab === 'matches' && (
              <div className="matches-tab">
                <h2>Your Matches</h2>
                {loading ? (
                  <p>Loading...</p>
                ) : !hasCompletedSurvey ? (
                  <p>You haven't completed the survey yet. Take the survey to see your matches!</p>
                ) : loadingMatches ? (
                  <p>Loading your matches...</p>
                ) : matchError ? (
                  <div className="error-message">
                    <p>{matchError}</p>
                    {cycleStatus?.status !== 'matches_available' && (
                      <p>Matches will be available once the processing period ends.</p>
                    )}
                  </div>
                ) : matches.length === 0 ? (
                  <div>
                    <p>Thank you for completing the survey! We're currently working on finding your best matches.</p>
                    {cycleStatus?.status === 'processing' ? (
                      <p>Matches are being processed and will be available soon.</p>
                    ) : (
                      <p>No matches found for you in this cycle. Please try again in the next matching cycle.</p>
                    )}
                  </div>
                ) : (
                  <div className="matches-list">
                    <p>We found {matches.length} potential match{matches.length !== 1 ? 'es' : ''} for you!</p>
                    {matches.map((match, index) => (
                      <div key={match.match_id || index} className="match-card">
                        <div className="match-info">
                          <h3>Match #{index + 1}</h3>
                          {match.name && <p className="match-name"><strong>{match.name}</strong></p>}
                          {match.instagram_handle && <p className="match-instagram">Instagram: {match.instagram_handle}</p>}
                          <p className="match-email">{match.email}</p>
                          <p className="match-score">Compatibility: {formatMatchScore(match.score)}</p>
                          {match.description && (
                            <p className="match-description">{match.description}</p>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
            
            {activeTab === 'about' && (
              <div className="about-tab">
                <h2>About WUCUPID</h2>
                <p>WUCUPID is a matchmaking service for WUSTL students to find romantic connections.</p>
                <p>Created with love for the WUSTL community.</p>
                
                <div className="about-cycle">
                  <h3>How Matching Works</h3>
                  <p>Our matching system works in monthly cycles:</p>
                  <ol>
                    <li><strong>Survey Period (30 days):</strong> Complete the compatibility survey</li>
                    <li><strong>Processing Period (3 days):</strong> Our algorithm analyzes responses</li>
                    <li><strong>Matches Available (3 days):</strong> See your compatible matches</li>
                    <li><strong>New Cycle:</strong> All survey and match data is cleared and a new cycle begins</li>
                  </ol>
                  <p><strong>Note:</strong> All match data is cleared at the end of each cycle, so be sure to connect with your matches before the viewing period ends!</p>
                </div>
                
                {/* Added Contact Info */}
                <p style={{ marginTop: '20px', fontStyle: 'italic' }}> 
                 Questions? Comments? Concerns? Want to delete your account? Email us at wu.cupid10@gmail.com
                </p>
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  );
} 