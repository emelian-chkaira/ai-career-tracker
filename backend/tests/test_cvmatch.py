from app.crawler import scoring
from app.services import cvmatch

CV = {"summary": "Flutter mobile engineer, five years in Dart, BLoC, Firebase, REST APIs.", "skills": ["Flutter", "Dart", "Firebase", "Python", "FastAPI"],
      "experience": [{"title": "Mobile Application Developer", "date": "Jan 2021 – Present", "desc": "", "tech": "Flutter", "bullets": ["Shipped Flutter apps to Google Play"]}], "languages": ["Arabic", "English"]}


def fit(title, desc, lang="english_ok", jt="job"):
    return scoring.fit(title, desc, "Amsterdam", jt, lang, {"cv_match": cvmatch.build(CV)}, None)


def test_summary_reads_the_whole_cv():
    m = cvmatch.build(CV)
    assert "flutter" in m["terms"] and "firebase" in m["terms"] and m["years"] >= 4 and not m["dutch"]


def test_matching_job_scores_high_and_unrelated_low():
    good, _ = fit("Flutter Developer", "Flutter, Dart and Firebase for our mobile app.")
    bad, _ = fit("Sales Manager", "Manage key accounts, CRM and negotiation.")
    assert good >= 75 and bad <= 25


def test_seniority_and_dutch_pull_the_score_down():
    senior, why = fit("Lead Flutter Engineer", "Flutter and Dart, 10 years.")
    plain, _ = fit("Flutter Engineer", "Flutter and Dart.")
    assert senior < plain and "years" in why
    dutch, why2 = fit("Flutter Developer", "Flutter Dart", lang="dutch_required")
    assert dutch <= 40 and "Dutch" in why2
