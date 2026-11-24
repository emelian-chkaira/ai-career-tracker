from app.crawler import scoring

DUTCH = "Jij vertaalt een complexe klantvraag naar een concreet ontwerp en weet dat te toetsen aan de gestelde omgevingseisen. Als Lead Engineer pak jij het technische en procesmatige projecten op voor onze klanten bij een groeiend bedrijf. Wij bieden een goede opleiding."
ENGLISH = "You will design and build the services that power our platform. We are looking for an engineer who works with the team and ships to production. Experience with Python is a plus."
GERMAN = "Wir suchen eine erfahrene Entwicklerin für unser Team. Sie arbeiten mit den Kunden und sind für die Planung der Projekte verantwortlich. Das ist eine Stelle mit viel Verantwortung und Ihre Aufgaben sind vielfältig."


def test_dutch_text_is_dutch_even_without_a_requirement_sentence():
    assert scoring.language("Lead Engineer E&I", DUTCH) == "dutch_required"


def test_english_text_stays_english_and_dutch_is_a_plus_is_kept():
    assert scoring.language("Backend Engineer", ENGLISH) == "english_ok"
    assert scoring.language("Backend Engineer", ENGLISH + " Dutch is a plus.") == "dutch_plus"


def test_german_is_not_english_either():
    assert scoring.language("Entwickler", GERMAN) == "non_english"
