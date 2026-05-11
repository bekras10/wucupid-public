class Answer:
    def __init__(self, text, value):
        self.text = text
        self.value = value

DEFAULT_ANSWERS = [
    Answer("Strongly agree", 2),
    Answer("Agree", 1),
    Answer("Neutral", 0),
    Answer("Disagree", -1),
    Answer("Strongly disagree", -2)
]

POLITICAL_ALIGNMENT_ANSWERS = [
    Answer("Conservative", -2),
    Answer("Somewhat conservative", -1),
    Answer("Neutral", 0),
    Answer("Somewhat Liberal", 1),
    Answer("Liberal", 2)
]

GENDER_ANSWERS = [
    Answer("Male", 1),
    Answer("Female", 2),
    Answer("Non-binary", 3)
]

ACADEMIC_YEAR_ANSWERS = [
    Answer("Freshman", 1),
    Answer("Sophomore", 2),
    Answer("Junior", 3),
    Answer("Senior", 4)
]

RELIGION_ANSWERS = [
    Answer("Christianity", 1),
    Answer("Islam", 2),
    Answer("Judaism", 3),
    Answer("Atheism", 4),
    Answer("Other", 5)
]

SEXUAL_ORIENTATION_ANSWERS = [
    Answer("Interested in men", 1),
    Answer("Interested in women", 2),
    Answer("Interested in everyone", 3)
]

class Question:
    def __init__(self, id, text, category, answers, reverse=False, multiple_choice=False, allow_no_preference=False, text_input=False, checkbox_option=None):
        self.id = id
        self.text = text
        self.category = category
        self.answers = answers
        self.reverse = reverse
        self.multiple_choice = multiple_choice
        self.allow_no_preference = allow_no_preference
        self.text_input = text_input
        self.checkbox_option = checkbox_option

# Filter questions
FILTER_QUESTIONS = [
    Question(-1, "What is your full name?", "Filters", [], text_input=True),
    Question(-10, "What is your Instagram handle?", "Filters", [], text_input=True, checkbox_option="I don't have Instagram"),
    Question(-2, "What is your gender?", "Filters", GENDER_ANSWERS),
    Question(-3, "What is your academic year?", "Filters", ACADEMIC_YEAR_ANSWERS),
    Question(-4, "I would prefer to be matched with people in these academic years:", "Filters", ACADEMIC_YEAR_ANSWERS, multiple_choice=True, allow_no_preference=True),
    Question(-5, "I most closely identify with this religion:", "Filters", RELIGION_ANSWERS),
    Question(-6, "I would prefer to be matched with people who follow these religions:", "Filters", RELIGION_ANSWERS, multiple_choice=True, allow_no_preference=True),
    Question(-7, "I most closely identify with this political view:", "Filters", POLITICAL_ALIGNMENT_ANSWERS),
    Question(-8, "I would prefer to be matched with people who hold these political views:", "Filters", POLITICAL_ALIGNMENT_ANSWERS, multiple_choice=True, allow_no_preference=True),
    Question(-9, "I am interested in:", "Filters", SEXUAL_ORIENTATION_ANSWERS)
]

# Define all survey questions - should match frontend questions
SURVEY_QUESTIONS = [
    # Personality (12 Questions)
    Question(1, "I enjoy meeting new people.", "Personality", DEFAULT_ANSWERS),
    Question(2, "I prefer spending time alone to recharge.", "Personality", DEFAULT_ANSWERS, reverse=True),
    Question(3, "I am open to trying new things and exploring new ideas.", "Personality", DEFAULT_ANSWERS),
    Question(4, "I appreciate art, literature, and music.", "Personality", DEFAULT_ANSWERS),
    Question(5, "I am organized and like to plan ahead.", "Personality", DEFAULT_ANSWERS),
    Question(6, "I pay close attention to details.", "Personality", DEFAULT_ANSWERS),
    Question(7, "I am empathetic and try to understand others' perspectives.", "Personality", DEFAULT_ANSWERS),
    Question(8, "I am cooperative and value getting along with others.", "Personality", DEFAULT_ANSWERS),
    Question(9, "I tend to get stressed out easily.", "Personality", DEFAULT_ANSWERS, reverse=True),
    Question(10, "I remain calm in difficult situations.", "Personality", DEFAULT_ANSWERS),
    Question(11, "I feel comfortable with myself.", "Personality", DEFAULT_ANSWERS),
    Question(12, "I finish what I start.", "Personality", DEFAULT_ANSWERS),

    # Religious/Political Preferences (7 Questions - removed question 19)
    Question(13, "Religion plays an important part in my daily life.", "Religious/Political Preferences", DEFAULT_ANSWERS),
    Question(14, "It's important to me that a potential partner shares the same political views as me.", "Religious/Political Preferences", DEFAULT_ANSWERS),
    Question(15, "Politics plays a large role in my life.", "Religious/Political Preferences", DEFAULT_ANSWERS),
    Question(16, "I hold my political beliefs strongly.", "Religious/Political Preferences", DEFAULT_ANSWERS),
    Question(17, "It's important to me that a potential partner shares the same religious views as me.", "Religious/Political Preferences", DEFAULT_ANSWERS),
    Question(18, "I believe government policies should be influenced by moral or religious principles.", "Religious/Political Preferences", DEFAULT_ANSWERS),
    # Removed question 19: "My political beliefs align most strongly with:" as it's redundant with filter question -7
    Question(20, "Government policies should strive to balance traditional values with the needs of a modern, diverse society.", "Religious/Political Preferences", DEFAULT_ANSWERS),

    # Intelligence/Cognitive Style (8 Questions)
    Question(21, "I enjoy solving puzzles and brain teasers.", "Intelligence/Cognitive Style", DEFAULT_ANSWERS),
    Question(22, "I often think about abstract or theoretical concepts.", "Intelligence/Cognitive Style", DEFAULT_ANSWERS),
    Question(23, "I find it easy to learn new things quickly.", "Intelligence/Cognitive Style", DEFAULT_ANSWERS),
    Question(24, "I prefer tasks that require logical analysis.", "Intelligence/Cognitive Style", DEFAULT_ANSWERS),
    Question(25, "I often reflect on complex problems and solutions.", "Intelligence/Cognitive Style", DEFAULT_ANSWERS),
    Question(26, "I enjoy tackling complex problems that require creative, non-linear thinking.", "Intelligence/Cognitive Style", DEFAULT_ANSWERS),
    Question(27, "I quickly grasp new concepts and can effectively apply them in real-world situations.", "Intelligence/Cognitive Style", DEFAULT_ANSWERS),
    Question(28, "I regularly analyze everyday situations to uncover underlying patterns or principles.", "Intelligence/Cognitive Style", DEFAULT_ANSWERS),

    # Interests (10 Questions)
    Question(29, "I enjoy reading books in various genres.", "Interests", DEFAULT_ANSWERS),
    Question(30, "I actively participate in sports or physical activities.", "Interests", DEFAULT_ANSWERS),
    Question(31, "I have a passion for music, art, or creative pursuits.", "Interests", DEFAULT_ANSWERS),
    Question(32, "I like to travel and explore new cultures.", "Interests", DEFAULT_ANSWERS),
    Question(33, "I am interested in technology and innovation.", "Interests", DEFAULT_ANSWERS),
    Question(34, "I enjoy engaging in social or community activities.", "Interests", DEFAULT_ANSWERS),
    Question(35, "I enjoy watching movies, documentaries, or live performances.", "Interests", DEFAULT_ANSWERS),
    Question(36, "I often experiment with cooking or trying new cuisines.", "Interests", DEFAULT_ANSWERS),
    Question(37, "I love spending time outdoors, whether hiking, gardening, or exploring nature.", "Interests", DEFAULT_ANSWERS),
    Question(38, "I actively seek out new hobbies and learning opportunities in my free time.", "Interests", DEFAULT_ANSWERS),

    # Interpersonal Style (6 Questions)
    Question(39, "I prefer frequent communication and check-ins with my partner.", "Interpersonal Style", DEFAULT_ANSWERS),
    Question(40, "I need time alone after arguments to process my thoughts.", "Interpersonal Style", DEFAULT_ANSWERS, reverse=True),
    Question(41, "I'm comfortable expressing affection openly.", "Interpersonal Style", DEFAULT_ANSWERS),
    Question(42, "I tend to avoid conflict even when something bothers me.", "Interpersonal Style", DEFAULT_ANSWERS, reverse=True),
    Question(43, "I like to make joint decisions rather than act independently.", "Interpersonal Style", DEFAULT_ANSWERS),
    Question(44, "I often reassure my partner when they're upset.", "Interpersonal Style", DEFAULT_ANSWERS),

    # Values & Beliefs (5 Questions)
    Question(45, "I believe fairness and equality are essential values.", "Values & Beliefs", DEFAULT_ANSWERS),
    Question(46, "Tradition and stability are more important than change.", "Values & Beliefs", DEFAULT_ANSWERS, reverse=True),
    Question(47, "I often think about how my actions affect the greater community.", "Values & Beliefs", DEFAULT_ANSWERS),
    Question(48, "I value personal freedom over social conformity.", "Values & Beliefs", DEFAULT_ANSWERS),
    Question(49, "I think loyalty to close friends and family should come before everything else.", "Values & Beliefs", DEFAULT_ANSWERS)
]

# Combined questions
ALL_QUESTIONS = FILTER_QUESTIONS + SURVEY_QUESTIONS 