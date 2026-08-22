from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True)
class CoverageSummary:
    total: int
    matched: int
    new: int
    review: int
    provinces: tuple[tuple[str, int], ...]
    categories: tuple[tuple[str, int], ...]

def summarize_coverage(report):
    provinces = {}
    categories = {}
    for item in report.items:
        c = item.observation.candidate
        province = c.province or "(missing)"
        provinces[province] = provinces.get(province, 0) + 1
        for category in c.categories:
            categories[category] = categories.get(category, 0) + 1
    summary = CoverageSummary(
        report.total, report.matched_count, report.new_count, report.review_count,
        tuple(sorted(provinces.items())), tuple(sorted(categories.items())),
    )
    if summary.total != summary.matched + summary.new + summary.review:
        raise ValueError("coverage accounting mismatch")
    return summary

def render_coverage(report):
    s = summarize_coverage(report)
    lines = [
        "DISCOVERY V2 COVERAGE DRY-RUN",
        "=" * 60,
        f"Source     : {report.source_name} ({report.source_type})",
        f"Query      : {report.query}",
        f"Candidates : {s.total}",
        f"Matched    : {s.matched}",
        f"New        : {s.new}",
        f"Review     : {s.review}",
        "",
        "Province coverage:",
    ]
    lines.extend(f"  {k}: {v}" for k, v in s.provinces)
    lines.append("")
    lines.append("Category coverage:")
    lines.extend(f"  {k}: {v}" for k, v in s.categories)
    return "\n".join(lines)
