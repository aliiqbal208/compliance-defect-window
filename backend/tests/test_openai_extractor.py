"""OpenAI backend: field mapping + text cross-check, with the API call mocked.

No key and no network. We stub the one method that talks to OpenAI and assert
the extractor turns a model response into the same SitePlan shape every other
backend produces, including the honest "Unable to determine" and the text-layer
cross-check that raises confidence on agreement.
"""
from app.extraction.openai_extractor import OpenAIExtractor
from app.extraction.schema import Source


def _raw():
    """A stand-in for the model's structured tool arguments."""
    box = {"x0": 0.4, "y0": 0.3, "x1": 0.5, "y1": 0.35}
    return {
        # agrees with the sample's text layer (5.2) -> confidence lifted to 0.95
        "front_setback": {"value": 5.2, "confidence": 0.7, "note": None,
                          "bbox": box},
        # not readable -> stays "Unable to determine", never guessed
        "building_height": {"value": None, "confidence": 0.0,
                            "note": "hidden by title block", "bbox": None},
    }


def test_openai_mapping_and_cross_check(sample_pdf, monkeypatch):
    extractor = OpenAIExtractor(model="gpt-4o", api_key="test-key")
    monkeypatch.setattr(extractor, "_call_model", lambda png, text: _raw())

    plan = extractor.extract(sample_pdf)

    front = plan.get("front_setback")
    assert front.value == 5.2
    assert front.source == Source.VISION
    assert front.bbox is not None
    # text layer confirms 5.2, so cross-check raises confidence
    assert front.confidence >= 0.95

    height = plan.get("building_height")
    assert height.value is None
    assert not height.determined
    assert height.note == "hidden by title block"

    assert plan.backend == "openai"


def test_openai_requires_a_key():
    try:
        OpenAIExtractor(model="gpt-4o", api_key="")
    except ValueError:
        return
    raise AssertionError("expected ValueError without an API key")
