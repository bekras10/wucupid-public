"use client";

import { useState, useEffect } from 'react';

interface FilterTag {
  type: string;
  value: string;
}

interface Match {
  match_id: number;
  email: string;
  name?: string;
  score: number;
  description?: string;
  shared_tags?: FilterTag[];
  date_created?: string;
}

interface MatchesProps {
  cycleStatus: {
    status: string;
    processing_end_date?: string;
  } | null;
}

export default function Matches({ cycleStatus }: MatchesProps) {
  const [matches, setMatches] = useState<Match[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchMatches = async () => {
      if (!cycleStatus || cycleStatus.status !== 'matches_available') {
        setLoading(false);
        return;
      }

      try {
        setLoading(true);
        const userEmail = localStorage.getItem('userEmail');
        if (!userEmail) {
          setError('User email not found');
          return;
        }

        const response = await fetch(`/api/matches/get_by_email?email=${encodeURIComponent(userEmail)}`);
        
        if (!response.ok) {
          throw new Error('Failed to fetch matches');
        }

        const data = await response.json();
        console.log("Matches received:", data.matches);
        // Log details about shared tags for each match
        if (data.matches && data.matches.length > 0) {
          data.matches.forEach((match: Match, index: number) => {
            console.log(`Match ${index + 1} with ${match.email}:`, {
              name: match.name,
              has_tags: Boolean(match.shared_tags),
              tag_count: match.shared_tags ? match.shared_tags.length : 0,
              tags: match.shared_tags
            });
          });
        }
        setMatches(data.matches || []);
      } catch (err) {
        console.error("Error fetching matches:", err);
        setError(err instanceof Error ? err.message : 'Failed to fetch matches');
      } finally {
        setLoading(false);
      }
    };

    fetchMatches();
  }, [cycleStatus]);

  // Helper function to render filter tags with appropriate styling
  const renderFilterTag = (tag: FilterTag, index: number) => {
    let tagClass = "filter-tag";
    
    // Apply specific styling based on tag type
    switch(tag.type) {
      case 'academic_year':
        tagClass += " academic-tag";
        break;
      case 'religion':
        tagClass += " religion-tag";
        break;
      case 'political_view':
        tagClass += " political-tag";
        break;
      case 'religion_preference':
        tagClass += " religion-preference-tag";
        break;
      case 'political_preference':
        tagClass += " political-preference-tag";
        break;
      default:
        tagClass += " default-tag";
    }
    
    return (
      <span key={index} className={tagClass}>
        {tag.value}
      </span>
    );
  };

  if (!cycleStatus) {
    return <div>Loading cycle status...</div>;
  }

  if (cycleStatus.status === 'survey_open') {
    return (
      <div className="matches-not-available">
        <h2>Matches Not Available Yet</h2>
        <p>The survey is still open. Matches will be available after the processing period.</p>
      </div>
    );
  }

  if (cycleStatus.status === 'processing') {
    return (
      <div className="matches-processing">
        <h2>Processing Matches</h2>
        <p>Your matches are being calculated. Please check back soon.</p>
        {cycleStatus.processing_end_date && (
          <p>Processing will be completed by: {new Date(cycleStatus.processing_end_date).toLocaleString()}</p>
        )}
      </div>
    );
  }

  if (loading) {
    return <div>Loading matches...</div>;
  }

  if (error) {
    return <div className="error">{error}</div>;
  }

  if (matches.length === 0) {
    return (
      <div className="no-matches">
        <h2>No Matches Found</h2>
        <p>We couldn't find any matches for you in this cycle.</p>
        <p>This could be because there weren't enough compatible users who completed the survey.</p>
      </div>
    );
  }

  return (
    <div className="matches">
      <h2>Your Matches</h2>
      <div className="matches-list">
        {matches.map((match, index) => (
          <div key={index} className="match-card">
            <div className="match-info">
              <h3>{match.name || 'Anonymous'}</h3>
              <div className="match-email">{match.email}</div>
              <div className="match-score">
                Match Score: {(match.score * 100).toFixed(1)}%
              </div>
              {match.shared_tags && match.shared_tags.length > 0 && (
                <div className="match-tags">
                  {match.shared_tags.map((tag, tagIndex) => 
                    renderFilterTag(tag, tagIndex)
                  )}
                </div>
              )}
            </div>
            {match.description && (
              <div className="match-description">
                {match.description}
              </div>
            )}
            <div className="match-actions">
              <button>View Profile</button>
              <button>Send Message</button>
            </div>
          </div>
        ))}
      </div>
      <div className="reminder">
        <p>Remember: Matches are only available for a limited time. Connect with your matches before the viewing period ends!</p>
      </div>
    </div>
  );
} 