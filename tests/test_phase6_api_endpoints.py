"""
Tests for Phase 6 FastAPI endpoints across all new specialized agents.
Uses TestClient to verify HTTP contracts, status codes, and deterministic outputs.
"""

from fastapi.testclient import TestClient
import pytest

from app.main import app

client = TestClient(app)


class TestDerivativesAPI:
    """Test Derivatives agent endpoints."""

    def test_calculate_call_payoff(self):
        resp = client.post(
            "/agents/derivatives/calculate",
            json={
                "contract_type": "call",
                "position": "long",
                "strike_price": 24000.0,
                "premium": 150.0,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["breakeven_price"] == 24150.0
        assert data["max_loss"] == 150.0

    def test_ask_derivatives(self):
        resp = client.post(
            "/agents/derivatives/ask",
            json={"query": "What is the maximum loss for a long put?"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "loss" in data["answer"].lower()
        assert data["disclaimer"] != ""


class TestPortfolioAPI:
    """Test Portfolio agent endpoints."""

    def test_get_portfolio_analytics(self):
        resp = client.get("/agents/portfolio?user_id=demo_user")
        assert resp.status_code == 200
        data = resp.json()
        assert "metrics" in data
        assert data["metrics"]["total_portfolio_value"] > 0

    def test_whatif_simulation(self):
        resp = client.post(
            "/agents/portfolio/whatif",
            json={
                "user_id": "demo_user",
                "symbol": "TCS",
                "percentage_change": -10.0,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "simulated_portfolio_value" in data
        assert data["portfolio_delta_value"] < 0


class TestNewsAPI:
    """Test Market News agent endpoints."""

    def test_ticker_news(self):
        resp = client.get("/agents/news/ticker/TCS?limit=2")
        assert resp.status_code == 200
        data = resp.json()
        assert "articles" in data
        assert "freshness" in data

    def test_macro_news(self):
        resp = client.get("/agents/news/macro?limit=2")
        assert resp.status_code == 200
        data = resp.json()
        assert "articles" in data


class TestQuizAPI:
    """Test Quiz agent endpoints."""

    def test_get_questions(self):
        resp = client.get("/agents/quiz/questions?limit=3")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) > 0
        assert "question" in data[0]
        # Should not reveal correct_option
        assert "correct_option" not in data[0]

    def test_submit_quiz(self):
        resp = client.post(
            "/agents/quiz/submit",
            json={
                "submissions": [{"question_id": "eq_beg_1", "selected_option": "A"}],
                "user_id": "api_test_user",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["score_percentage"] == 100.0
        assert data["correct_count"] == 1


class TestOnboardingAPI:
    """Test Onboarding agent endpoints."""

    def test_get_capabilities(self):
        resp = client.get("/agents/onboarding/capabilities")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 8
        domains = [c["domain"] for c in data]
        assert "derivatives" in domains
        assert "portfolio" in domains
        assert "news" in domains
        assert "quiz" in domains

    def test_get_faqs(self):
        resp = client.get("/agents/onboarding/faqs")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 3
        faq_ids = [f["id"] for f in data]
        assert "faq_memory_deletion" in faq_ids
