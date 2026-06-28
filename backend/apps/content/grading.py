from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Any, TypeVar

from django.core.exceptions import ValidationError

from .models import Question


class Grader(ABC):
    """Validate content/answer_key and grade a response for one kind."""

    auto_gradable: bool = True

    @abstractmethod
    def validate(self, content: dict[str, Any], answer_key: dict[str, Any]) -> None:
        pass

    @abstractmethod
    def is_correct(self, answer_key: dict[str, Any], response: Any) -> bool:
        pass


_REGISTRY: dict[str, Grader] = {}
G = TypeVar("G", bound=Grader)


def register(kind: str) -> Callable[[type[G]], type[G]]:
    def deco(cls: type[G]) -> type[G]:
        _REGISTRY[str(kind)] = cls()
        return cls

    return deco


def get_grader(kind: str) -> Grader | None:
    return _REGISTRY.get(kind)


def _option_ids(content: dict[str, Any]) -> set[str]:
    options = content.get("options")
    if not isinstance(options, list) or not options:
        raise ValidationError("content.options must be a non-empty list.")
    ids: list[str] = []
    for opt in options:
        if not isinstance(opt, dict) or "id" not in opt or "text" not in opt:
            raise ValidationError("Each option must have an 'id' and 'text'.")
        ids.append(str(opt["id"]))
    if len(ids) != len(set(ids)):
        raise ValidationError("Option IDs must be unique.")
    return set(ids)


def _ids_from_entries(entries: list[Any], label: str) -> set[str]:
    ids: list[str] = []
    for e in entries:
        if not isinstance(e, dict) or "id" not in e or "text" not in e:
            raise ValidationError(f"Each {label} item must have an 'id' and 'text'.")
        ids.append(str(e["id"]))
    if len(ids) != len(set(ids)):
        raise ValidationError(f"{label} IDs must be unique.")
    return set(ids)


@register(Question.Kind.SINGLE_CHOICE)
class SingleChoiceGrader(Grader):
    def validate(self, content: dict[str, Any], answer_key: dict[str, Any]) -> None:
        ids = _option_ids(content)
        correct = answer_key.get("correct")
        if not isinstance(correct, str):
            raise ValidationError("answer_key.correct must be an option id (str).")
        if correct not in ids:
            raise ValidationError(f"answer_key.correct '{correct}' not in options.")

    def is_correct(self, answer_key: dict[str, Any], response: Any) -> bool:
        return bool(response == answer_key.get("correct"))


@register(Question.Kind.MULTI_CHOICE)
class MultiChoiceGrader(Grader):
    def validate(self, content: dict[str, Any], answer_key: dict[str, Any]) -> None:
        ids = _option_ids(content)
        correct = answer_key.get("correct")
        if not isinstance(correct, list) or not correct:
            raise ValidationError("answer_key.correct — a non-empty list of IDs.")
        unknown = {str(c) for c in correct} - ids
        if unknown:
            raise ValidationError(f"Unknown ids in answer_key: {sorted(unknown)}.")

    def is_correct(self, answer_key: dict[str, Any], response: Any) -> bool:
        if not isinstance(response, list):
            return False
        correct = answer_key.get("correct", [])
        return {str(r) for r in response} == {str(c) for c in correct}


@register(Question.Kind.SHORT_ANSWER)
class ShortAnswerGrader(Grader):
    def validate(self, content: dict[str, Any], answer_key: dict[str, Any]) -> None:
        accepted = answer_key.get("accepted")
        if not isinstance(accepted, list) or not accepted:
            raise ValidationError("answer_key.accepted — a non-empty list of strings.")
        if not all(isinstance(a, str) for a in accepted):
            raise ValidationError("answer_key.accepted contains only strings.")

    def is_correct(self, answer_key: dict[str, Any], response: Any) -> bool:
        if not isinstance(response, str):
            return False
        norm = response.strip().casefold()
        return any(norm == a.strip().casefold() for a in answer_key.get("accepted", []))


@register(Question.Kind.GAP_FILL)
class GapFillGrader(Grader):
    def validate(self, content: dict[str, Any], answer_key: dict[str, Any]) -> None:
        gaps = content.get("gaps")
        if not isinstance(gaps, list) or not gaps:
            raise ValidationError("content.gaps must be a non-empty list.")
        gap_ids: list[str] = []
        for gap in gaps:
            if not isinstance(gap, dict) or "id" not in gap:
                raise ValidationError("Each gap must have an 'id'.")
            gap_ids.append(str(gap["id"]))
        if len(gap_ids) != len(set(gap_ids)):
            raise ValidationError("Gap IDs must be unique.")
        answers = answer_key.get("answers")
        if not isinstance(answers, dict) or not answers:
            raise ValidationError("answer_key.answers must be a non-empty object.")
        if set(answers) != set(gap_ids):
            raise ValidationError("answer_key.answers keys must match gap IDs.")
        for accepted in answers.values():
            if not isinstance(accepted, list) or not accepted:
                raise ValidationError(
                    "Each gap needs a non-empty list of accepted answers."
                )
            if not all(isinstance(a, str) for a in accepted):
                raise ValidationError("Accepted answers must be strings.")

    def is_correct(self, answer_key: dict[str, Any], response: Any) -> bool:
        if not isinstance(response, dict):
            return False
        answers = answer_key.get("answers", {})
        for gap_id, accepted in answers.items():
            given = response.get(gap_id)
            if not isinstance(given, str):
                return False
            norm = given.strip().casefold()
            if not any(norm == a.strip().casefold() for a in accepted):
                return False
        return True


@register(Question.Kind.MATCHING)
class MatchingGrader(Grader):
    def validate(self, content: dict[str, Any], answer_key: dict[str, Any]) -> None:
        left, right = content.get("left"), content.get("right")
        if not isinstance(left, list) or not left:
            raise ValidationError("content.left must be a non-empty list.")
        if not isinstance(right, list) or not right:
            raise ValidationError("content.right must be a non-empty list.")
        left_ids = _ids_from_entries(left, "left")
        right_ids = _ids_from_entries(right, "right")
        pairs = answer_key.get("pairs")
        if not isinstance(pairs, dict) or not pairs:
            raise ValidationError("answer_key.pairs must be a non-empty object.")
        if {str(k) for k in pairs} != left_ids:
            raise ValidationError(
                "answer_key.pairs must map every left ID exactly once."
            )
        unknown = {str(v) for v in pairs.values()} - right_ids
        if unknown:
            raise ValidationError(f"Unknown right IDs in pairs: {sorted(unknown)}.")

    def is_correct(self, answer_key: dict[str, Any], response: Any) -> bool:
        if not isinstance(response, dict):
            return False
        pairs = answer_key.get("pairs", {})
        return {str(k): str(v) for k, v in response.items()} == {
            str(k): str(v) for k, v in pairs.items()
        }


@register(Question.Kind.ESSAY)
class EssayGrader(Grader):
    auto_gradable = False

    def validate(self, content: dict[str, Any], answer_key: dict[str, Any]) -> None:
        criteria = content.get("criteria")
        if not isinstance(criteria, list) or not criteria:
            raise ValidationError("content.criteria must be a non-empty list.")
        ids: list[str] = []
        for c in criteria:
            if not isinstance(c, dict) or {"id", "text", "points"} - c.keys():
                raise ValidationError("Each criterion needs id, text, points.")
            if not isinstance(c["points"], int | float) or c["points"] <= 0:
                raise ValidationError("Criterion points must be a positive number.")
            ids.append(str(c["id"]))
        if len(ids) != len(set(ids)):
            raise ValidationError("Criterion IDs must be unique.")

    def is_correct(self, answer_key: dict[str, Any], response: Any) -> bool:
        return False
