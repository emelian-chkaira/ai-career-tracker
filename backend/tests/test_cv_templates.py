

def test_hidden_items_are_left_out():
    from app.cvtools import latexcv
    cv = {"name": "A", "email": "a@x.nl", "experience": [{"heading": "Visible Co", "title": "Visible Co", "bullets": []}, {"heading": "Secret Co", "title": "Secret Co", "bullets": [], "hidden": True}]}
    for t in ("classic", "compact", "modern"):
        out = latexcv.render(cv, t); assert "Visible Co" in out and "Secret Co" not in out
