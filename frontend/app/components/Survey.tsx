"use client";

import { useState, useEffect } from 'react';
import { SURVEY_QUESTIONS } from '../survey/surveyData';

interface SurveyProps {
  cycleStatus: {
    status: string;
    survey_start_date?: string;
    survey_end_date?: string;
  } | null;
}

export default function Survey({ cycleStatus }: SurveyProps) {
  const [currentQuestion, setCurrentQuestion] = useState(0);
  const [answers, setAnswers] = useState<Record<number, number>>({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [surveyCompleted, setSurveyCompleted] = useState(false);

  useEffect(() => {
    // Check if user has already completed the survey
    const checkSurveyStatus = async () => {
      const userEmail = localStorage.getItem('userEmail');
      if (!userEmail) return;

      try {
        const response = await fetch(`http://127.0.0.1:5000/api/survey/check?email=${encodeURIComponent(userEmail)}`);
        
        if (response.ok) {
          const data = await response.json();
          setSurveyCompleted(data.hasCompletedSurvey);
        }
      } catch (err) {
        console.error("Error checking survey status:", err);
      }
    };

    checkSurveyStatus();
  }, []);

  const handleAnswer = (questionId: number, value: number) => {
    setAnswers(prev => ({
      ...prev,
      [questionId]: value
    }));
  };

  const handleSubmit = async () => {
    if (Object.keys(answers).length < SURVEY_QUESTIONS.length) {
      setError('Please answer all questions before submitting.');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/api/survey/submit`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          answers
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to submit survey');
      }

      // Survey submitted successfully
      setSurveyCompleted(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to submit survey');
    } finally {
      setLoading(false);
    }
  };

  if (!cycleStatus) {
    return <div>Loading cycle status...</div>;
  }

  if (cycleStatus.status !== 'survey_open') {
    return (
      <div className="survey-closed">
        <h2>Survey is currently closed</h2>
        <p>The survey is only open during the survey period.</p>
        {cycleStatus.survey_start_date && cycleStatus.survey_end_date && (
          <div className="survey-dates">
            <p>Current survey period: {new Date(cycleStatus.survey_start_date).toLocaleDateString()} - {new Date(cycleStatus.survey_end_date).toLocaleDateString()}</p>
          </div>
        )}
      </div>
    );
  }

  if (surveyCompleted) {
    return (
      <div className="survey-complete">
        <h2>Survey Complete!</h2>
        <p>Thank you for completing the survey for this cycle.</p>
        <p>Your responses have been saved and will be used to find your matches.</p>
      </div>
    );
  }

  const question = SURVEY_QUESTIONS[currentQuestion];

  return (
    <div className="survey">
      <div className="progress">
        Question {currentQuestion + 1} of {SURVEY_QUESTIONS.length}
      </div>
      
      <div className="question">
        <h3>{question.text}</h3>
        <div className="answers">
          {question.answers.map((answer, index) => (
            <button
              key={index}
              className={answers[question.id] === answer.value ? 'selected' : ''}
              onClick={() => handleAnswer(question.id, answer.value)}
            >
              {answer.text}
            </button>
          ))}
        </div>
      </div>

      <div className="navigation">
        <button
          onClick={() => setCurrentQuestion(prev => Math.max(0, prev - 1))}
          disabled={currentQuestion === 0}
        >
          Previous
        </button>
        <button
          onClick={() => setCurrentQuestion(prev => Math.min(SURVEY_QUESTIONS.length - 1, prev + 1))}
          disabled={currentQuestion === SURVEY_QUESTIONS.length - 1}
        >
          Next
        </button>
        {currentQuestion === SURVEY_QUESTIONS.length - 1 && (
          <button onClick={handleSubmit} disabled={loading}>
            {loading ? 'Submitting...' : 'Submit'}
          </button>
        )}
      </div>

      {error && <div className="error">{error}</div>}
    </div>
  );
} 