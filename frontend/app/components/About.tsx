"use client";

export default function About() {
  return (
    <div className="about">
      <h2>About WUCUPID</h2>
      
      <section className="about-section">
        <h3>How It Works</h3>
        <p>
          WUCUPID is a matching system designed specifically for the WUSTL community.
          Our algorithm analyzes your survey responses to find compatible matches based on:
        </p>
        <ul>
          <li>Personality traits</li>
          <li>Religious and political preferences</li>
          <li>Cognitive style and intelligence</li>
          <li>Shared interests and values</li>
        </ul>
      </section>
      
      <section className="about-section">
        <h3>The Matching Process</h3>
        <ol>
          <li>
            <strong>Survey Period (30 days)</strong>
            <p>Complete the matching survey to help us understand your preferences and personality.</p>
          </li>
          <li>
            <strong>Processing Period (3 days)</strong>
            <p>Our algorithm analyzes all survey responses to find the best matches.</p>
          </li>
          <li>
            <strong>Matches Available (3 days)</strong>
            <p>View your matches and connect with potential partners.</p>
          </li>
          <li>
            <strong>New Cycle</strong>
            <p>The process starts again with a fresh survey period.</p>
          </li>
        </ol>
      </section>
      
      <section className="about-section">
        <h3>Important Notes</h3>
        <ul>
          <li>All user data is cleared at the end of each cycle</li>
          <li>You must complete the survey in each cycle to receive matches</li>
          <li>Matches are only available during the designated viewing period</li>
          <li>Be sure to connect with your matches before the viewing period ends</li>
        </ul>
      </section>
    </div>
  );
} 