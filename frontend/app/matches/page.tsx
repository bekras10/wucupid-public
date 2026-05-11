"use client";

import React, { useState, useEffect } from 'react';
import { redirect } from 'next/navigation';
import Matches from '../components/Matches';

export default function MatchesPage() {
  const [cycleStatus, setCycleStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchCycleStatus = async () => {
      try {
        const response = await fetch(`/api/cycle/status`);
        if (!response.ok) {
          throw new Error('Failed to fetch cycle status');
        }
        const data = await response.json();
        setCycleStatus(data);
      } catch (err) {
        console.error("Error fetching cycle status:", err);
        setError(err instanceof Error ? err.message : 'Failed to fetch cycle status');
      } finally {
        setLoading(false);
      }
    };

    fetchCycleStatus();
  }, []);

  if (loading) {
    return <div>Loading...</div>;
  }

  if (error) {
    return <div className="error">{error}</div>;
  }

  return <Matches cycleStatus={cycleStatus} />;
}
