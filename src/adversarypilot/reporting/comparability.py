"""Comparability checker — flags non-comparable result sets."""

from __future__ import annotations

from adversarypilot.models.results import EvaluationResult


class ComparabilityChecker:
    """Detects and flags reasons why ASR comparisons between result sets may be invalid."""

    def check_pairwise(
        self, a: EvaluationResult, b: EvaluationResult
    ) -> list[str]:
        """Return list of reasons why two results are not directly comparable."""
        flags = []
        ca, cb = a.comparability, b.comparability

        if ca.judge_type != cb.judge_type:
            flags.append(
                f"Different judge types: {ca.judge_type.value} vs {cb.judge_type.value}"
            )

        if ca.judge_model_version and cb.judge_model_version:
            if ca.judge_model_version != cb.judge_model_version:
                flags.append(
                    f"Different judge model versions: "
                    f"{ca.judge_model_version} vs {cb.judge_model_version}"
                )

        if ca.success_criteria_hash and cb.success_criteria_hash:
            if ca.success_criteria_hash != cb.success_criteria_hash:
                flags.append("Different success criteria definitions")

        if ca.input_slice_id and cb.input_slice_id:
            if ca.input_slice_id != cb.input_slice_id:
                flags.append(
                    f"Different input slices: {ca.input_slice_id} vs {cb.input_slice_id}"
                )

        if ca.dataset_version and cb.dataset_version:
            if ca.dataset_version != cb.dataset_version:
                flags.append("Different dataset versions")

        if ca.target_profile_hash and cb.target_profile_hash:
            if ca.target_profile_hash != cb.target_profile_hash:
                flags.append("Different target configurations")

        if ca.random_seed_policy != cb.random_seed_policy:
            flags.append(
                f"Different seed policies: {ca.random_seed_policy} vs {cb.random_seed_policy}"
            )

        if ca.num_trials != cb.num_trials:
            flags.append(
                f"Different trial counts: {ca.num_trials} vs {cb.num_trials}"
            )

        return flags

    def check_group(
        self, results: list[EvaluationResult]
    ) -> list[str]:
        """Check a group of results for comparability, returning all unique warnings."""
        if len(results) < 2:
            return []

        all_flags: set[str] = set()
        base = results[0]
        for other in results[1:]:
            flags = self.check_pairwise(base, other)
            all_flags.update(flags)

        return sorted(all_flags)

    def find_comparable_groups(
        self, results: list[EvaluationResult]
    ) -> dict[str, list[EvaluationResult]]:
        """Group results by their comparable_group_key."""
        groups: dict[str, list[EvaluationResult]] = {}
        for result in results:
            key = result.comparability.comparable_group_key or "ungrouped"
            groups.setdefault(key, []).append(result)
        return groups
