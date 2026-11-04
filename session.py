import uuid
from datetime import datetime
from typing import Optional

_sessions: dict = {}

DEPARTMENT_KEYWORDS = {
    "computer_science": ["cse", "computer science", "cs", "software", "programming", "coding", "computing"],
    "electronics":      ["ece", "electronics", "communication", "vlsi", "embedded"],
    "mechanical":       ["mechanical", "mech", "automobile", "manufacturing"],
    "civil":            ["civil", "construction", "structural"],
    "electrical":       ["eee", "electrical", "power systems"],
    "biomedical":       ["biomedical", "bme", "medical devices"],
    "biotechnology":    ["biotech", "biotechnology", "genetic"],
    "robotics":         ["robotics", "mechatronics", "automation", "robot"],
    "aerospace":        ["aerospace", "aeronautical", "aviation"],
    "information_tech": ["it", "information technology", "computer applications"],
    "data_science":     ["data science", "data analytics", "ml", "ai", "machine learning"],
    "chemical":         ["chemical", "chemistry"],
}

INTENT_KEYWORDS = {
    "department":  ["department", "dept", "courses", "faculty", "professors", "clubs", "achievements", "syllabus"],
    "admission":   ["admission", "apply", "application", "deadline", "eligibility", "fee", "fees", "srmjeee", "entrance", "cutoff", "join"],
    "hostel":      ["hostel", "accommodation", "room", "dormitory", "mess", "food", "canteen"],
    "transport":   ["transport", "bus", "shuttle", "travel", "commute"],
    "campus_life": ["campus life", "events", "fest", "club", "cultural", "sports", "student life"],
    "placement":   ["placement", "job", "recruit", "salary", "package", "company"],
    "scholarship": ["scholarship", "fee waiver", "financial aid", "merit"],
}


def create_session():
    sid = str(uuid.uuid4())
    _sessions[sid] = {
        "id": sid, "created_at": datetime.now().isoformat(),
        "department": None, "intent_history": [],
        "topics_discussed": [], "admission_interest": False, "messages": []
    }
    return sid


def get_session(sid):
    return _sessions.get(sid)


def detect_department(text):
    text_lower = text.lower()
    for dept, keywords in DEPARTMENT_KEYWORDS.items():
        if any(kw in text_lower for kw in keywords):
            return dept
    return None


def detect_intent(text):
    text_lower = text.lower()
    for intent, keywords in INTENT_KEYWORDS.items():
        if any(kw in text_lower for kw in keywords):
            return intent
    return "general"


def rewrite_query(query, session):
    dept = session.get("department")
    intent = detect_intent(query)
    if dept and detect_department(query) is None:
        dept_display = dept.replace("_", " ").title()
        if intent == "hostel":
            return f"hostel facilities for {dept_display} department students at SRMIST Kattankulathur"
        elif intent == "transport":
            return f"transport facilities for {dept_display} students at SRMIST Kattankulathur"
        elif intent == "placement":
            return f"placement statistics and companies for {dept_display} department at SRMIST"
        elif intent == "admission":
            return f"admission process eligibility and fees for {dept_display} at SRMIST Kattankulathur"
        elif intent == "campus_life":
            return f"student life clubs and events for {dept_display} at SRMIST"
        elif intent == "department":
            return f"{dept_display} department courses faculty and achievements at SRMIST"
    return query


def update_session(sid, user_message, assistant_message):
    session = _sessions.get(sid)
    if not session:
        return
    detected_dept = detect_department(user_message)
    if detected_dept:
        session["department"] = detected_dept
    intent = detect_intent(user_message)
    session["intent_history"].append(intent)
    if intent not in session["topics_discussed"]:
        session["topics_discussed"].append(intent)
    if intent == "admission":
        session["admission_interest"] = True
    session["messages"].append({"role": "user", "content": user_message})
    session["messages"].append({"role": "assistant", "content": assistant_message})
    if len(session["messages"]) > 20:
        session["messages"] = session["messages"][-20:]
