from pathlib import Path
from streamlit.testing.v1 import AppTest

APP = Path(__file__).resolve().parents[1] / "src/dashboard/app.py"


def test_dashboard_controls_and_assistant():
    app = AppTest.from_file(str(APP), default_timeout=30).run()
    assert not app.exception
    assert app.metric[0].value == "400"
    initial = app.metric[1].value
    next(s for s in app.slider if s.label.startswith("Minimum speed")).set_value(40.0).run()
    assert not app.exception
    assert app.metric[1].value == "0" and initial != "0"
    next(b for b in app.button if b.label == "Ask assistant").click().run()
    assert not app.exception
    assert any("0 of 400" in m.value for m in app.markdown)
    next(b for b in app.button if b.label == "Reset replay").click().run()
    assert not app.exception
    next(r for r in app.radio if r.label == "Input mode").set_value("FastF1 session").run()
    assert not app.exception
    assert any(x.label == "Grand Prix" for x in app.text_input)
