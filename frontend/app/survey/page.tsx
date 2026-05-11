"use client";
import { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { ALL_QUESTIONS, FILTER_QUESTIONS, SURVEY_QUESTIONS, Question } from './surveyData';
import { ensureCsrfCookie, getCsrfToken } from '../lib/csrf';

// Survey stages
type SurveyStage = 'intro' | 'filters' | 'questions' | 'complete';

// Survey state structure
interface SurveyState {
  stage: SurveyStage;
  currentQuestionIndex: number;
  answers: Record<number, any>;
  noPreferenceChecked: Record<number, boolean>;
  checkboxStates: Record<number, boolean>;
  name: string;
}

export default function SurveyPage() {
  const router = useRouter();
  const [stage, setStage] = useState<SurveyStage>('intro');
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0);
  const [answers, setAnswers] = useState<Record<number, any>>({});
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [name, setName] = useState('');
  const [noPreferenceChecked, setNoPreferenceChecked] = useState<Record<number, boolean>>({});
  const [checkboxStates, setCheckboxStates] = useState<Record<number, boolean>>({});
  const [saveMessageVisible, setSaveMessageVisible] = useState(false);

  // Progress percentage
  const getProgress = () => {
    const totalQuestions = ALL_QUESTIONS.length;
    const answeredCount = Object.keys(answers).length;
    return Math.round((answeredCount / totalQuestions) * 100);
  };

  // Save survey state to both localStorage and backend
  const saveSurveyState = useCallback(async () => {
    if (stage === 'complete') return; // Don't save if survey is completed
    
    const surveyState: SurveyState = {
      stage,
      currentQuestionIndex,
      answers,
      noPreferenceChecked,
      checkboxStates,
      name
    };
    
    if (typeof window !== 'undefined') {
      // Save to localStorage as backup
      localStorage.setItem('surveyState', JSON.stringify(surveyState));
      
      // Save to backend
      const email = localStorage.getItem('userEmail');
      if (email) {
        try {
          await fetch('/api/survey/progress', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'X-CSRF-Token': getCsrfToken(),
            },
            body: JSON.stringify({
              email,
              stage,
              currentQuestionIndex,
              answers,
              noPreferenceChecked,
              checkboxStates,
              name
            }),
          });
          
          // Show save message
          setSaveMessageVisible(true);
          setTimeout(() => setSaveMessageVisible(false), 2000);
        } catch (error) {
          console.error('Failed to save progress to backend:', error);
          // Still show save message since localStorage worked
          setSaveMessageVisible(true);
          setTimeout(() => setSaveMessageVisible(false), 2000);
        }
      }
    }
  }, [stage, currentQuestionIndex, answers, noPreferenceChecked, checkboxStates, name]);

  // Load survey state from backend and localStorage
  useEffect(() => {
    const loadSurveyState = async () => {
      if (typeof window === 'undefined') return;
      
      // Ensure CSRF cookie is set early in the user session
      await ensureCsrfCookie();
      
      // Check if we should force start fresh (e.g., from dashboard "Start Survey" button)
      const urlParams = new URLSearchParams(window.location.search);
      const forceStart = urlParams.get('start') === 'true';
      
      if (forceStart) {
        // Clear any existing survey state and start fresh
        localStorage.removeItem('surveyState');
        const email = localStorage.getItem('userEmail');
        if (email) {
          try {
            // Clear backend progress too
            await fetch('/api/survey/progress', {
              method: 'POST',
              headers: {
                'Content-Type': 'application/json',
                'X-CSRF-Token': getCsrfToken(),
              },
              body: JSON.stringify({
                email,
                stage: 'intro',
                currentQuestionIndex: 0,
                answers: {},
                noPreferenceChecked: {},
                checkboxStates: {},
                name: ''
              }),
            });
          } catch (error) {
            console.error('Failed to clear backend progress:', error);
          }
        }
        // Clear the URL parameter
        window.history.replaceState({}, '', '/survey');
        // Stay on intro stage (which is the default)
        return;
      }
      
      // Try to load from backend first
      const email = localStorage.getItem('userEmail');
      if (email) {
        try {
          const response = await fetch(`/api/survey/progress?email=${encodeURIComponent(email)}`);
          if (response.ok) {
            const data = await response.json();
            if (data.hasProgress && data.progress) {
              const progress = data.progress;
              if (progress.stage !== 'complete') {
                setStage(progress.stage || 'intro');
                setCurrentQuestionIndex(progress.currentQuestionIndex || 0);
                setAnswers(progress.answers || {});
                setNoPreferenceChecked(progress.noPreferenceChecked || {});
                setCheckboxStates(progress.checkboxStates || {});
                setName(progress.name || '');
                return; // Backend data loaded successfully
              }
            }
          }
        } catch (error) {
          console.error('Failed to load progress from backend:', error);
        }
      }
      
      // Fallback to localStorage if backend fails
      const savedState = localStorage.getItem('surveyState');
      if (savedState) {
        try {
          const parsedState: SurveyState = JSON.parse(savedState);
          // Only load saved state if the survey isn't complete
          if (parsedState.stage !== 'complete') {
            setStage(parsedState.stage);
            setCurrentQuestionIndex(parsedState.currentQuestionIndex);
            setAnswers(parsedState.answers);
            setNoPreferenceChecked(parsedState.noPreferenceChecked);
            setCheckboxStates(parsedState.checkboxStates);
            setName(parsedState.name || '');
          }
        } catch (error) {
          console.error('Error parsing saved survey state:', error);
        }
      }
    };
    
    loadSurveyState();
  }, []);

  // Save state when navigating away
  useEffect(() => {
    const handleBeforeUnload = () => {
      saveSurveyState();
    };
    
    window.addEventListener('beforeunload', handleBeforeUnload);
    
    return () => {
      window.removeEventListener('beforeunload', handleBeforeUnload);
    };
  }, [saveSurveyState]);

  // Handle starting the survey
  const startSurvey = () => {
    setStage('filters');
    saveSurveyState();
  };

  // Handle single-choice answer selection
  const handleAnswer = (questionId: number, value: any) => {
    setAnswers(prev => ({
      ...prev,
      [questionId]: value
    }));
    saveSurveyState();
  };

  // Handle text input for name
  const handleTextInput = (questionId: number, value: string) => {
    setAnswers(prev => ({
      ...prev,
      [questionId]: value
    }));
    setName(value);
    saveSurveyState();
  };

  // Handle checkbox option
  const handleCheckboxOption = (questionId: number) => {
    setCheckboxStates(prev => {
      const newState = {
        ...prev,
        [questionId]: !prev[questionId]
      };
      
      // If checking the checkbox, clear the text input
      if (newState[questionId]) {
        setAnswers(prevAnswers => {
          const newAnswers = {
            ...prevAnswers,
            [questionId]: null
          };
          setTimeout(() => saveSurveyState(), 0);
          return newAnswers;
        });
      } else {
        // If unchecking, reset text input to default value for Instagram question
        if (questionId === -10) {
          setAnswers(prevAnswers => {
            const newAnswers = {
              ...prevAnswers,
              [questionId]: '@'
            };
            setTimeout(() => saveSurveyState(), 0);
            return newAnswers;
          });
        }
      }
      
      return newState;
    });
  };

  // Handle multiple choice answers
  const handleMultipleChoice = (questionId: number, value: number) => {
    setAnswers(prev => {
      const currentValues = Array.isArray(prev[questionId]) ? prev[questionId] : [];
      
      // Check if value already exists
      if (currentValues.includes(value)) {
        // Remove the value
        const newAnswers = {
          ...prev,
          [questionId]: currentValues.filter((v: number) => v !== value)
        };
        setTimeout(() => saveSurveyState(), 0);
        return newAnswers;
      } else {
        // Add the value
        const newAnswers = {
          ...prev,
          [questionId]: [...currentValues, value]
        };
        setTimeout(() => saveSurveyState(), 0);
        return newAnswers;
      }
    });
  };

  // Handle "no preference" option
  const handleNoPreference = (questionId: number) => {
    setNoPreferenceChecked(prev => {
      const newState = {
        ...prev,
        [questionId]: !prev[questionId]
      };
      
      // If checking "no preference", clear all other selections
      if (newState[questionId]) {
        setAnswers(prevAnswers => {
          const newAnswers = {
            ...prevAnswers,
            [questionId]: "no preference"
          };
          setTimeout(() => saveSurveyState(), 0);
          return newAnswers;
        });
      } else {
        // If unchecking "no preference", set to empty array
        setAnswers(prevAnswers => {
          const newAnswers = {
            ...prevAnswers,
            [questionId]: []
          };
          setTimeout(() => saveSurveyState(), 0);
          return newAnswers;
        });
      }
      
      return newState;
    });
  };

  // Handle navigation through questions
  const goToPrevious = () => {
    if (currentQuestionIndex > 0) {
      setCurrentQuestionIndex(currentQuestionIndex - 1);
      saveSurveyState();
    }
  };

  const goToNext = () => {
    const currentQuestion = getCurrentQuestion();
    
    // Validate that the current question has been answered
    const answer = answers[currentQuestion.id];
    let isValid = false;
    
    if (!currentQuestion) {
      isValid = false;
    } else if (currentQuestion.textInput) {
      // Text input validation - allow checkbox option as alternative
      if (currentQuestion.checkboxOption && checkboxStates[currentQuestion.id]) {
        isValid = true; // Checkbox is checked, so it's valid
      } else {
        isValid = answer !== undefined && answer.trim() !== '' && 
                  !(currentQuestion.id === -10 && answer.trim() === '@');
      }
    } else if (currentQuestion.multipleChoice) {
      // Multiple choice validation: either "no preference" OR at least one selection
      isValid = answer === "no preference" || 
                (Array.isArray(answer) && answer.length > 0);
    } else {
      // Single choice validation
      isValid = answer !== undefined;
    }
    
    if (!isValid) {
      alert('Please answer this question before continuing.');
      return;
    }
    
    if (stage === 'filters') {
      if (currentQuestionIndex < FILTER_QUESTIONS.length - 1) {
        setCurrentQuestionIndex(currentQuestionIndex + 1);
        saveSurveyState();
      } else {
        // Transition from filters to main survey questions
        setStage('questions');
        setCurrentQuestionIndex(0); // Start at the first main survey question
        saveSurveyState();
      }
    } else if (stage === 'questions') {
      if (currentQuestionIndex < SURVEY_QUESTIONS.length - 1) {
        setCurrentQuestionIndex(currentQuestionIndex + 1);
        saveSurveyState();
      }
      // If it's the last question, the submit button will be shown instead
    }
  };

  // Move from filter questions to main survey questions
  const moveToMainSurvey = () => {
    // Ensure all filter questions are answered
    const allFiltersAnswered = FILTER_QUESTIONS.every(q => {
      const answer = answers[q.id];
      if (q.textInput) {
        // Allow checkbox option as alternative
        if (q.checkboxOption && checkboxStates[q.id]) {
          return true; // Checkbox is checked, so it's valid
        } else {
          return answer !== undefined && answer.trim() !== '' && 
                 !(q.id === -10 && answer.trim() === '@');
        }
      } else if (q.multipleChoice) {
        return answer === "no preference" || 
               (Array.isArray(answer) && answer.length > 0);
      } else {
        return answer !== undefined;
      }
    });
    
    if (!allFiltersAnswered) {
      alert('Please answer all filter questions before continuing.');
      return;
    }
    
    setStage('questions');
    setCurrentQuestionIndex(0); // Start at the first main survey question
    saveSurveyState();
  };

  // Handle survey submission
  const handleSubmit = async () => {
    // Check if all questions are answered
    const allQuestionsAnswered = ALL_QUESTIONS.every(q => {
      const answer = answers[q.id];
      if (q.textInput) {
        // Allow checkbox option as alternative
        if (q.checkboxOption && checkboxStates[q.id]) {
          return true; // Checkbox is checked, so it's valid
        } else {
          return answer !== undefined && answer.trim() !== '' && 
                 !(q.id === -10 && answer.trim() === '@');
        }
      } else if (q.multipleChoice) {
        return answer === "no preference" || 
               (Array.isArray(answer) && answer.length > 0);
      } else {
        return answer !== undefined;
      }
    });
    
    if (!allQuestionsAnswered) {
      alert('Please answer all questions before submitting.');
      return;
    }

    setIsSubmitting(true);
    try {
      // Backend now derives user from session; send only answers + filters
      // Backend now handles reverse scoring; send raw answers
      const processedAnswers = { ...answers };

      // Extract filter data
      const filterData = {
        name: processedAnswers[-1],
        instagram_handle: checkboxStates[-10] ? null : processedAnswers[-10],
        gender: processedAnswers[-2],
        academic_year: processedAnswers[-3],
        preferred_years: processedAnswers[-4],
        religion: processedAnswers[-5],
        preferred_religions: processedAnswers[-6],
        political_view: processedAnswers[-7],
        preferred_political_views: processedAnswers[-8],
        sexual_orientation: processedAnswers[-9]
      };

      // Remove filter question data from processed answers
      FILTER_QUESTIONS.forEach(question => {
        delete processedAnswers[question.id];
      });

      // Send the processed answers to the backend
      const response = await fetch('/api/survey/submit', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRF-Token': getCsrfToken(),
        },
        credentials: 'include',
        body: JSON.stringify({ 
          answers: processedAnswers,
          filters: filterData
        }),
      });

      if (response.ok) {
        // Save completion flag to localStorage
        if (typeof window !== 'undefined') {
          localStorage.setItem('surveyCompleted', 'true');
          // Clear survey state since it's completed
          localStorage.removeItem('surveyState');
        }
        
        // Clear backend progress as well since survey is completed
        const email = localStorage.getItem('userEmail');
        if (email) {
          try {
            await fetch('/api/survey/progress', {
              method: 'POST',
              headers: {
                'Content-Type': 'application/json',
              },
              body: JSON.stringify({
                email,
                stage: 'complete',
                currentQuestionIndex: 0,
                answers: {},
                noPreferenceChecked: {},
                checkboxStates: {},
                name: ''
              }),
            });
          } catch (error) {
            console.error('Failed to clear backend progress after completion:', error);
          }
        }
        
        setStage('complete');
      } else {
        if (response.status === 401) {
          alert('Please log in to submit your survey.');
          router.push('/auth/login');
          return;
        }
        const data = await response.json();
        alert(`Failed to submit survey: ${data.message}`);
      }
    } catch (error) {
      console.error('Error submitting survey:', error);
      alert('Failed to submit survey. Please try again later.');
    } finally {
      setIsSubmitting(false);
    }
  };

  // Handle back to dashboard
  const handleBackToDashboard = () => {
    saveSurveyState();
    router.push('/dashboard');
  };

  // Introduction page component
  const IntroPage = () => (
    <div className="survey-intro">
      <h1>WUCUPID Matching Survey</h1>
      <div className="intro-content">
        <p>Welcome to the WUCUPID matching survey! This survey will help us find you the best possible matches based on your preferences and personality.</p>
        
        <h2>Instructions:</h2>
        <ul>
          <li>The survey begins with some basic filter questions about yourself and your preferences.</li>
          <li>You'll then answer questions about your personality, interests, and values.</li>
          <li>Answer honestly - this helps us find your best matches!</li>
          <li>You can use the Previous and Next buttons to review your answers.</li>
          <li>At the end, you'll submit your responses to see your matches.</li>
          <li>Your progress is automatically saved if you need to return later.</li>
        </ul>
        
        <p>Ready to find your perfect match? Let's get started!</p>
        
        <button onClick={startSurvey} className="start-survey-button">
          Begin Survey
        </button>
      </div>
    </div>
  );

  // Get the current question based on the stage
  const getCurrentQuestion = () => {
    if (stage === 'filters') {
      return FILTER_QUESTIONS[currentQuestionIndex];
    } else if (stage === 'questions') {
      return SURVEY_QUESTIONS[currentQuestionIndex];
    }
    return null;
  };

  // Question page component
  const QuestionPage = () => {
    const currentQuestion = getCurrentQuestion();
    if (!currentQuestion) return null;
    
    return (
      <div className="survey-question">
        <div className="question-header">
          <h2>{currentQuestion.category}</h2>
          <div className="progress-container">
            <div className="progress-bar" style={{ width: `${getProgress()}%` }}></div>
            <span className="progress-text">
              {stage === 'filters' ? 
                `Filter Question ${currentQuestionIndex + 1} of ${FILTER_QUESTIONS.length}` : 
                `Question ${currentQuestionIndex + 1} of ${SURVEY_QUESTIONS.length}`}
              ({getProgress()}%)
            </span>
          </div>
        </div>
        
        <div className="question-content">
          <h3>{currentQuestion.text}</h3>
          
          {currentQuestion.textInput ? (
            <div className="text-input-container">
              <input
                type="text"
                placeholder={currentQuestion.id === -1 ? "Enter your full name" : "Enter your Instagram handle"}
                value={currentQuestion.id === -10 ? 
                  (answers[currentQuestion.id] || '@') : 
                  (answers[currentQuestion.id] || '')
                }
                onChange={(e) => {
                  let value = e.target.value;
                  // For Instagram handle, ensure it starts with @ and has content after @
                  if (currentQuestion.id === -10) {
                    if (value === '' || !value.startsWith('@')) {
                      value = '@';
                    }
                  }
                  handleTextInput(currentQuestion.id, value);
                  // Keep focus on the input
                  e.target.focus();
                }}
                onKeyDown={(e) => {
                  // For Instagram handle, prevent deleting the @ symbol
                  if (currentQuestion.id === -10 && e.key === 'Backspace') {
                    const value = e.currentTarget.value;
                    if (value === '@' || value.length <= 1) {
                      e.preventDefault();
                    }
                  }
                }}
                autoFocus
                className="name-input"
                disabled={checkboxStates[currentQuestion.id]}
              />
              
              {currentQuestion.checkboxOption && (
                <div className="checkbox-option">
                  <input
                    type="checkbox"
                    id={`checkbox-${currentQuestion.id}`}
                    checked={checkboxStates[currentQuestion.id] || false}
                    onChange={() => handleCheckboxOption(currentQuestion.id)}
                  />
                  <label htmlFor={`checkbox-${currentQuestion.id}`}>
                    {currentQuestion.checkboxOption}
                  </label>
                </div>
              )}
            </div>
          ) : currentQuestion.multipleChoice ? (
            <div className="multiple-choice-options">
              {currentQuestion.answers.map((answer, idx) => (
                <div key={idx} className="multiple-choice-option">
                  <input
                    type="checkbox"
                    id={`answer-${currentQuestion.id}-${idx}`}
                    checked={Array.isArray(answers[currentQuestion.id]) && answers[currentQuestion.id].includes(answer.value)}
                    onChange={() => handleMultipleChoice(currentQuestion.id, answer.value)}
                    disabled={noPreferenceChecked[currentQuestion.id]}
                  />
                  <label htmlFor={`answer-${currentQuestion.id}-${idx}`}>{answer.text}</label>
                </div>
              ))}
              
              {currentQuestion.allowNoPreference && (
                <div className="no-preference-option">
                  <input
                    type="checkbox"
                    id={`no-preference-${currentQuestion.id}`}
                    checked={noPreferenceChecked[currentQuestion.id] || false}
                    onChange={() => handleNoPreference(currentQuestion.id)}
                  />
                  <label htmlFor={`no-preference-${currentQuestion.id}`}>No preference</label>
                </div>
              )}
            </div>
          ) : (
            <div className="answer-options">
              {currentQuestion.answers.map((answer, idx) => (
                <button 
                  key={idx}
                  className={`answer-button ${answers[currentQuestion.id] === answer.value ? 'selected' : ''}`}
                  onClick={() => handleAnswer(currentQuestion.id, answer.value)}
                >
                  {answer.text}
                </button>
              ))}
            </div>
          )}
          
          <div className="navigation-buttons">
            <button 
              onClick={goToPrevious} 
              disabled={currentQuestionIndex === 0}
              className="nav-button prev"
            >
              Previous
            </button>
            
            {stage === 'filters' && currentQuestionIndex === FILTER_QUESTIONS.length - 1 ? (
              <button 
                onClick={moveToMainSurvey}
                className="nav-button next"
              >
                Continue to Survey
              </button>
            ) : stage === 'questions' && currentQuestionIndex === SURVEY_QUESTIONS.length - 1 ? (
              <button 
                onClick={handleSubmit}
                disabled={isSubmitting}
                className="nav-button submit"
              >
                {isSubmitting ? 'Submitting...' : 'Submit'}
              </button>
            ) : (
              <button 
                onClick={goToNext}
                className="nav-button next"
              >
                Next
              </button>
            )}
          </div>
        </div>
      </div>
    );
  };

  // Completion page component
  const CompletionPage = () => (
    <div className="survey-complete">
      <h1>Survey Complete!</h1>
      <p>Thank you for completing the WUCUPID matching survey, {(answers[-1] || name || 'there').split(' ')[0]}!</p>
      <p>Your responses have been saved and will be used to find your perfect matches.</p>
      <p>Head back to the dashboard to see your matches soon!</p>
      
      <button onClick={() => router.push('/dashboard')} className="return-button">
        Return to Dashboard
      </button>
    </div>
  );

  // Render the appropriate stage
  return (
    <div className="survey-container">
      {stage === 'intro' && <IntroPage />}
      {(stage === 'filters' || stage === 'questions') && (
        <>
          <QuestionPage />
          <div className="back-to-dashboard-container">
            <button 
              onClick={handleBackToDashboard} 
              className="back-to-dashboard-button"
            >
              Back to Dashboard
            </button>
          </div>
        </>
      )}
      {stage === 'complete' && <CompletionPage />}
      
      {/* Save state message */}
      <div className={`save-state-message ${saveMessageVisible ? 'visible' : ''}`}>
        Progress saved
      </div>
    </div>
  );
}
