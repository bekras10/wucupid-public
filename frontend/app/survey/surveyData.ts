export type Answer = {
  text: string;
  value: number;
};

export const DEFAULT_ANSWERS: Answer[] = [
  { text: "Strongly agree", value: 2 },
  { text: "Agree", value: 1 },
  { text: "Neutral", value: 0 },
  { text: "Disagree", value: -1 },
  { text: "Strongly disagree", value: -2 }
];

export const POLITICAL_ALIGNMENT_ANSWERS: Answer[] = [
  { text: "Conservative", value: -2 },
  { text: "Somewhat conservative", value: -1 },
  { text: "Neutral", value: 0 },
  { text: "Somewhat Liberal", value: 1 },
  { text: "Liberal", value: 2 }
];

export const GENDER_ANSWERS: Answer[] = [
  { text: "Male", value: 1 },
  { text: "Female", value: 2 },
  { text: "Non-binary", value: 3 }
];

export const ACADEMIC_YEAR_ANSWERS: Answer[] = [
  { text: "Freshman", value: 1 },
  { text: "Sophomore", value: 2 },
  { text: "Junior", value: 3 },
  { text: "Senior", value: 4 }
];

export const RELIGION_ANSWERS: Answer[] = [
  { text: "Christianity", value: 1 },
  { text: "Islam", value: 2 },
  { text: "Judaism", value: 3 },
  { text: "Atheism", value: 4 },
  { text: "Other", value: 5 }
];

export const SEXUAL_ORIENTATION_ANSWERS: Answer[] = [
  { text: "Interested in men", value: 1 },
  { text: "Interested in women", value: 2 },
  { text: "Interested in everyone", value: 3 }
];

export type Question = {
  id: number;
  text: string;
  category: string;
  answers: Answer[];
  reverse?: boolean;
  multipleChoice?: boolean;
  allowNoPreference?: boolean;
  textInput?: boolean;
  checkboxOption?: string;
};

// Filter questions are at the beginning (IDs F1-F8) to separate them from the original questions
export const FILTER_QUESTIONS: Question[] = [
  {
    id: -1, // Using negative IDs to distinguish from original survey questions
    text: "What is your full name?",
    category: "Filters",
    answers: [], // No predefined answers for text input
    textInput: true
  },
  {
    id: -10, // New Instagram handle question
    text: "What is your Instagram handle?",
    category: "Filters",
    answers: [], // No predefined answers for text input
    textInput: true,
    checkboxOption: "I don't have Instagram"
  },
  {
    id: -2,
    text: "What is your gender?",
    category: "Filters",
    answers: GENDER_ANSWERS
  },
  {
    id: -3,
    text: "What is your academic year?",
    category: "Filters",
    answers: ACADEMIC_YEAR_ANSWERS
  },
  {
    id: -4,
    text: "I would prefer to be matched with people in these academic years:",
    category: "Filters",
    answers: ACADEMIC_YEAR_ANSWERS,
    multipleChoice: true,
    allowNoPreference: true
  },
  {
    id: -5,
    text: "I most closely identify with this religion:",
    category: "Filters",
    answers: RELIGION_ANSWERS
  },
  {
    id: -6,
    text: "I would prefer to be matched with people who follow these religions:",
    category: "Filters",
    answers: RELIGION_ANSWERS,
    multipleChoice: true,
    allowNoPreference: true
  },
  {
    id: -7,
    text: "I most closely identify with this political view:",
    category: "Filters",
    answers: POLITICAL_ALIGNMENT_ANSWERS
  },
  {
    id: -8,
    text: "I would prefer to be matched with people who hold these political views:",
    category: "Filters",
    answers: POLITICAL_ALIGNMENT_ANSWERS,
    multipleChoice: true,
    allowNoPreference: true
  },
  {
    id: -9,
    text: "I am interested in:",
    category: "Filters",
    answers: SEXUAL_ORIENTATION_ANSWERS
  }
];

export const SURVEY_QUESTIONS: Question[] = [
  // Personality (12 Questions)
  {
    id: 1,
    text: "I enjoy meeting new people.",
    category: "Personality",
    answers: DEFAULT_ANSWERS
  },
  {
    id: 2,
    text: "I prefer spending time alone to recharge.",
    category: "Personality",
    answers: DEFAULT_ANSWERS,
    reverse: true // Introversion vs. Extraversion
  },
  {
    id: 3,
    text: "I am open to trying new things and exploring new ideas.",
    category: "Personality",
    answers: DEFAULT_ANSWERS
  },
  {
    id: 4,
    text: "I appreciate art, literature, and music.",
    category: "Personality",
    answers: DEFAULT_ANSWERS
  },
  {
    id: 5,
    text: "I am organized and like to plan ahead.",
    category: "Personality",
    answers: DEFAULT_ANSWERS
  },
  {
    id: 6,
    text: "I pay close attention to details.",
    category: "Personality",
    answers: DEFAULT_ANSWERS
  },
  {
    id: 7,
    text: "I am empathetic and try to understand others' perspectives.",
    category: "Personality",
    answers: DEFAULT_ANSWERS
  },
  {
    id: 8,
    text: "I am cooperative and value getting along with others.",
    category: "Personality",
    answers: DEFAULT_ANSWERS
  },
  {
    id: 9,
    text: "I tend to get stressed out easily.",
    category: "Personality",
    answers: DEFAULT_ANSWERS,
    reverse: true // Emotional stability vs. Neuroticism
  },
  {
    id: 10,
    text: "I remain calm in difficult situations.",
    category: "Personality",
    answers: DEFAULT_ANSWERS
  },
  {
    id: 11,
    text: "I feel comfortable with myself.",
    category: "Personality",
    answers: DEFAULT_ANSWERS
  },
  {
    id: 12,
    text: "I finish what I start.",
    category: "Personality",
    answers: DEFAULT_ANSWERS
  },

  // Religious/Political Preferences (7 Questions - removed question 19)
  {
    id: 13,
    text: "Religion plays an important part in my daily life.",
    category: "Religious/Political Preferences",
    answers: DEFAULT_ANSWERS
  },
  {
    id: 14,
    text: "It's important to me that a potential partner shares the same political views as me.",
    category: "Religious/Political Preferences",
    answers: DEFAULT_ANSWERS
  },
  {
    id: 15,
    text: "Politics plays a large role in my life.",
    category: "Religious/Political Preferences",
    answers: DEFAULT_ANSWERS
  },
  {
    id: 16,
    text: "I hold my political beliefs strongly.",
    category: "Religious/Political Preferences",
    answers: DEFAULT_ANSWERS
  },
  {
    id: 17,
    text: "It's important to me that a potential partner shares the same religious views as me.",
    category: "Religious/Political Preferences",
    answers: DEFAULT_ANSWERS
  },
  {
    id: 18,
    text: "I believe government policies should be influenced by moral or religious principles.",
    category: "Religious/Political Preferences",
    answers: DEFAULT_ANSWERS
  },
  {
    id: 20,
    text: "Government policies should strive to balance traditional values with the needs of a modern, diverse society.",
    category: "Religious/Political Preferences",
    answers: DEFAULT_ANSWERS
  },

  // Intelligence/Cognitive Style (8 Questions)
  {
    id: 21,
    text: "I enjoy solving puzzles and brain teasers.",
    category: "Intelligence/Cognitive Style",
    answers: DEFAULT_ANSWERS
  },
  {
    id: 22,
    text: "I often think about abstract or theoretical concepts.",
    category: "Intelligence/Cognitive Style",
    answers: DEFAULT_ANSWERS
  },
  {
    id: 23,
    text: "I find it easy to learn new things quickly.",
    category: "Intelligence/Cognitive Style",
    answers: DEFAULT_ANSWERS
  },
  {
    id: 24,
    text: "I prefer tasks that require logical analysis.",
    category: "Intelligence/Cognitive Style",
    answers: DEFAULT_ANSWERS
  },
  {
    id: 25,
    text: "I often reflect on complex problems and solutions.",
    category: "Intelligence/Cognitive Style",
    answers: DEFAULT_ANSWERS
  },
  {
    id: 26,
    text: "I enjoy tackling complex problems that require creative, non-linear thinking.",
    category: "Intelligence/Cognitive Style",
    answers: DEFAULT_ANSWERS
  },
  {
    id: 27,
    text: "I quickly grasp new concepts and can effectively apply them in real-world situations.",
    category: "Intelligence/Cognitive Style",
    answers: DEFAULT_ANSWERS
  },
  {
    id: 28,
    text: "I regularly analyze everyday situations to uncover underlying patterns or principles.",
    category: "Intelligence/Cognitive Style",
    answers: DEFAULT_ANSWERS
  },

  // Interests (10 Questions)
  {
    id: 29,
    text: "I enjoy reading books in various genres.",
    category: "Interests",
    answers: DEFAULT_ANSWERS
  },
  {
    id: 30,
    text: "I actively participate in sports or physical activities.",
    category: "Interests",
    answers: DEFAULT_ANSWERS
  },
  {
    id: 31,
    text: "I have a passion for music, art, or creative pursuits.",
    category: "Interests",
    answers: DEFAULT_ANSWERS
  },
  {
    id: 32,
    text: "I like to travel and explore new cultures.",
    category: "Interests",
    answers: DEFAULT_ANSWERS
  },
  {
    id: 33,
    text: "I am interested in technology and innovation.",
    category: "Interests",
    answers: DEFAULT_ANSWERS
  },
  {
    id: 34,
    text: "I enjoy engaging in social or community activities.",
    category: "Interests",
    answers: DEFAULT_ANSWERS
  },
  {
    id: 35,
    text: "I enjoy watching movies, documentaries, or live performances.",
    category: "Interests",
    answers: DEFAULT_ANSWERS
  },
  {
    id: 36,
    text: "I often experiment with cooking or trying new cuisines.",
    category: "Interests",
    answers: DEFAULT_ANSWERS
  },
  {
    id: 37,
    text: "I love spending time outdoors, whether hiking, gardening, or exploring nature.",
    category: "Interests",
    answers: DEFAULT_ANSWERS
  },
  {
    id: 38,
    text: "I actively seek out new hobbies and learning opportunities in my free time.",
    category: "Interests",
    answers: DEFAULT_ANSWERS
  },
  
  // Interpersonal Style (6 Questions)
  {
    id: 39,
    text: "I prefer frequent communication and check-ins with my partner.",
    category: "Interpersonal Style",
    answers: DEFAULT_ANSWERS
  },
  {
    id: 40,
    text: "I need time alone after arguments to process my thoughts.",
    category: "Interpersonal Style",
    answers: DEFAULT_ANSWERS,
    reverse: true
  },
  {
    id: 41,
    text: "I'm comfortable expressing affection openly.",
    category: "Interpersonal Style",
    answers: DEFAULT_ANSWERS
  },
  {
    id: 42,
    text: "I tend to avoid conflict even when something bothers me.",
    category: "Interpersonal Style",
    answers: DEFAULT_ANSWERS,
    reverse: true
  },
  {
    id: 43,
    text: "I like to make joint decisions rather than act independently.",
    category: "Interpersonal Style",
    answers: DEFAULT_ANSWERS
  },
  {
    id: 44,
    text: "I often reassure my partner when they're upset.",
    category: "Interpersonal Style",
    answers: DEFAULT_ANSWERS
  },

  // Values & Beliefs (5 Questions)
  {
    id: 45,
    text: "I believe fairness and equality are essential values.",
    category: "Values & Beliefs",
    answers: DEFAULT_ANSWERS
  },
  {
    id: 46,
    text: "Tradition and stability are more important than change.",
    category: "Values & Beliefs",
    answers: DEFAULT_ANSWERS,
    reverse: true
  },
  {
    id: 47,
    text: "I often think about how my actions affect the greater community.",
    category: "Values & Beliefs",
    answers: DEFAULT_ANSWERS
  },
  {
    id: 48,
    text: "I value personal freedom over social conformity.",
    category: "Values & Beliefs",
    answers: DEFAULT_ANSWERS
  },
  {
    id: 49,
    text: "I think loyalty to close friends and family should come before everything else.",
    category: "Values & Beliefs",
    answers: DEFAULT_ANSWERS
  },

];

// Combined questions (filters + survey questions)
export const ALL_QUESTIONS: Question[] = [...FILTER_QUESTIONS, ...SURVEY_QUESTIONS];