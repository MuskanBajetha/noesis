import torch
import torch.nn as nn
import numpy as np
import os
import json
from datetime import datetime
from sqlalchemy.orm import Session
from app.models.database import Answer, Question, MasteryScore, Student

# ── DKT Model Architecture ───────────────────────────────

class DKTModel(nn.Module):
    """
    Deep Knowledge Tracing using LSTM.
    Input: sequence of (question, correct) pairs
    Output: probability of mastery for each concept
    """
    def __init__(self, num_concepts: int, hidden_size: int = 64, num_layers: int = 2):
        super(DKTModel, self).__init__()
        self.num_concepts = num_concepts
        self.hidden_size = hidden_size
        self.input_size = num_concepts * 2  # concept + correct/incorrect

        self.lstm = nn.LSTM(
            input_size=self.input_size,
            hidden_size=hidden_size,
            num_layers=num_layers,
            batch_first=True,
            dropout=0.2
        )
        self.output_layer = nn.Linear(hidden_size, num_concepts)
        self.sigmoid = nn.Sigmoid()

    def forward(self, x):
        lstm_out, _ = self.lstm(x)
        output = self.output_layer(lstm_out)
        return self.sigmoid(output)


# ── Knowledge Tracer ─────────────────────────────────────

class KnowledgeTracer:
    """
    Manages knowledge tracing for students.
    Uses DKT model to estimate mastery probabilities.
    """

    TOPICS = [
        "Newton's Laws", "Gravity", "Photosynthesis",
        "Cell Division", "Algebra", "Thermodynamics",
        "Evolution", "Quantum Physics", "Radar", "General"
    ]

    UNDERSTANDING_TO_SCORE = {
        "none": 0.0,
        "partial": 0.4,
        "good": 0.7,
        "excellent": 1.0
    }

    def __init__(self):
        self.num_concepts = len(self.TOPICS)
        self.topic_to_idx = {t: i for i, t in enumerate(self.TOPICS)}
        self.model = DKTModel(num_concepts=self.num_concepts)
        self.model.eval()
        self.model_path = "dkt_model.pth"

        if os.path.exists(self.model_path):
            try:
                self.model.load_state_dict(torch.load(self.model_path, weights_only=True))
                print("✅ DKT model loaded from disk")
            except Exception:
                print("⚠️ Could not load DKT model, using fresh model")

    def _get_topic_idx(self, topic: str) -> int:
        return self.topic_to_idx.get(topic, self.topic_to_idx["General"])

    def _encode_interaction(self, topic: str, correct: float) -> torch.Tensor:
        """Encode a single interaction as a one-hot vector."""
        vector = torch.zeros(self.num_concepts * 2)
        topic_idx = self._get_topic_idx(topic)

        if correct >= 0.5:
            vector[topic_idx] = 1.0  # correct
        else:
            vector[self.num_concepts + topic_idx] = 1.0  # incorrect

        return vector

    def estimate_mastery(self, interaction_history: list) -> dict:
        """
        Estimate mastery probabilities from interaction history.

        Args:
            interaction_history: list of {"topic": str, "score": float}

        Returns:
            dict of {topic: mastery_probability}
        """
        if not interaction_history:
            return {topic: 0.5 for topic in self.TOPICS}

        # Build sequence
        sequence = []
        for interaction in interaction_history[-20:]:  # Last 20 interactions
            topic = interaction.get("topic", "General")
            score = interaction.get("score", 0.5)
            vector = self._encode_interaction(topic, score)
            sequence.append(vector)

        # Run through model
        with torch.no_grad():
            x = torch.stack(sequence).unsqueeze(0)  # (1, seq_len, input_size)
            output = self.model(x)
            last_output = output[0, -1, :]  # Last timestep predictions

        mastery = {}
        for topic, idx in self.topic_to_idx.items():
            mastery[topic] = round(float(last_output[idx]), 3)

        return mastery

    def get_student_mastery(self, student_id: int, db: Session) -> dict:
        """Get mastery estimates for a student from their answer history."""

        # Get answer history
        answers = (
            db.query(Answer, Question)
            .join(Question, Answer.question_id == Question.id)
            .filter(Question.session_id.in_(
                db.query(Question.session_id).filter(
                    Question.topic.isnot(None)
                )
            ))
            .order_by(Answer.created_at)
            .limit(50)
            .all()
        )

        # Build interaction history
        interaction_history = []
        for answer, question in answers:
            score = self.UNDERSTANDING_TO_SCORE.get(
                answer.understanding_level or "partial", 0.4
            )
            interaction_history.append({
                "topic": question.topic,
                "score": score
            })

        if not interaction_history:
            # Fall back to mastery scores from DB
            mastery_scores = db.query(MasteryScore).filter(
                MasteryScore.student_id == student_id
            ).all()

            result = {topic: 0.5 for topic in self.TOPICS}
            for m in mastery_scores:
                if m.topic in result:
                    result[m.topic] = m.score
            return result

        return self.estimate_mastery(interaction_history)

    def get_next_topic_recommendation(self, mastery: dict) -> dict:
        """
        Recommend next topic based on mastery levels.
        Uses zone of proximal development - not too easy, not too hard.
        """
        recommendations = []

        for topic, score in mastery.items():
            if topic == "General":
                continue
            if 0.3 <= score <= 0.75:
                priority = "high"
            elif score < 0.3:
                priority = "remedial"
            else:
                priority = "advanced"

            recommendations.append({
                "topic": topic,
                "mastery": score,
                "priority": priority,
                "reason": self._get_recommendation_reason(score)
            })

        recommendations.sort(key=lambda x: (
            0 if x["priority"] == "high" else
            1 if x["priority"] == "remedial" else 2
        ))

        return {
            "recommendations": recommendations[:3],
            "focus_topic": recommendations[0]["topic"] if recommendations else None
        }

    def _get_recommendation_reason(self, score: float) -> str:
        if score < 0.3:
            return "Needs foundational work"
        elif score < 0.5:
            return "Building understanding"
        elif score < 0.75:
            return "Good progress, keep going"
        elif score < 0.9:
            return "Almost mastered"
        else:
            return "Mastered — try advanced challenges"

    def train_on_student_data(self, student_id: int, db: Session) -> dict:
        """
        Fine-tune the DKT model on a student's interaction data.
        Simple online learning approach.
        """
        answers = (
            db.query(Answer, Question)
            .join(Question, Answer.question_id == Question.id)
            .order_by(Answer.created_at)
            .all()
        )

        if len(answers) < 3:
            return {"status": "insufficient_data", "interactions": len(answers)}

        optimizer = torch.optim.Adam(self.model.parameters(), lr=0.001)
        criterion = nn.BCELoss()
        self.model.train()

        total_loss = 0
        sequence = []

        for answer, question in answers:
            score = self.UNDERSTANDING_TO_SCORE.get(
                answer.understanding_level or "partial", 0.4
            )
            vector = self._encode_interaction(question.topic, score)
            sequence.append(vector)

        if len(sequence) < 2:
            return {"status": "insufficient_data"}

        x = torch.stack(sequence[:-1]).unsqueeze(0)
        target_idx = self._get_topic_idx(answers[-1][1].topic)
        target_score = self.UNDERSTANDING_TO_SCORE.get(
            answers[-1][0].understanding_level or "partial", 0.4
        )

        optimizer.zero_grad()
        output = self.model(x)
        last_pred = output[0, -1, target_idx]
        target = torch.tensor([target_score])
        loss = criterion(last_pred.unsqueeze(0), target)
        loss.backward()
        optimizer.step()
        total_loss = loss.item()

        self.model.eval()
        torch.save(self.model.state_dict(), self.model_path)

        return {
            "status": "trained",
            "loss": round(total_loss, 4),
            "interactions_used": len(sequence)
        }


# ── Singleton Instance ───────────────────────────────────
knowledge_tracer = KnowledgeTracer()