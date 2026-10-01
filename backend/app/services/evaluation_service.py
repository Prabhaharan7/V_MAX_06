"""
================================================================================
SIF Sentinel AI - Dataset Evaluation & Model Accuracy Benchmark Service
SIH 2026 Problem Statement PS 26165 (Oil India Limited)
================================================================================
Compares model predictions (SIF label, confidence, LSR tags) against
ground-truth labels (ground_truth_sif_label, ground_truth_lsr, ground_truth_split)
to compute comprehensive statistical accuracy metrics, confusion matrices, and
split-based evaluation (Train vs Test vs Val).
================================================================================
"""

from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.entities import Report, SIFLabel
from app.schemas.dataset import (
    AccuracyReportResponse,
    BatchListResponse,
    BatchSummaryItem,
    ConfusionMatrix,
    LSRRuleAccuracy,
    SIFMetrics,
    SplitEvaluation,
)


def compute_sif_metrics(
    tp: int,
    fp: int,
    fn: int,
    tn: int,
) -> SIFMetrics:
    """
    Computes standard classification evaluation metrics for SIF precursor detection.
    """
    total = tp + fp + fn + tn
    if total == 0:
        return SIFMetrics(
            accuracy=0.0,
            precision=0.0,
            recall=0.0,
            f1_score=0.0,
            specificity=0.0,
            total_evaluated=0,
            sif_count=0,
            non_sif_count=0,
        )

    accuracy = (tp + tn) / total
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
    specificity = tn / (tn + fp) if (tn + fp) > 0 else 0.0

    return SIFMetrics(
        accuracy=round(accuracy, 4),
        precision=round(precision, 4),
        recall=round(recall, 4),
        f1_score=round(f1, 4),
        specificity=round(specificity, 4),
        total_evaluated=total,
        sif_count=tp + fn,
        non_sif_count=tn + fp,
    )


def normalize_rule_name(rule: str) -> str:
    if not rule:
        return ""
    norm = str(rule).strip().lower().replace(" ", "").replace("_", "").replace("-", "")
    return norm.replace("z", "s")


def match_lsr_rule(gt_rule: str, pred_rule: Optional[str], tags: List[Any]) -> bool:
    """
    Determines if model predicted the correct Life-Saving Rule.
    Checks primary_lsr match or secondary tag containment with normalization.
    """
    if not gt_rule:
        return False

    gt_norm = normalize_rule_name(gt_rule)

    # Check primary_lsr
    if pred_rule:
        pred_norm = normalize_rule_name(pred_rule)
        if gt_norm in pred_norm or pred_norm in gt_norm:
            return True

    # Check tags
    for t in tags:
        tag_rule = getattr(t, "lsr_rule", "") if hasattr(t, "lsr_rule") else str(t)
        tag_norm = normalize_rule_name(tag_rule)
        if gt_norm in tag_norm or tag_norm in gt_norm:
            return True

    return False


async def evaluate_batch_accuracy(
    db: AsyncSession,
    batch_id: Optional[str] = None,
) -> AccuracyReportResponse:
    """
    Evaluates model prediction accuracy against ground-truth labels for a given batch
    or across the entire database.
    """
    query = (
        select(Report)
        .options(
            selectinload(Report.lsr_tags),
            selectinload(Report.barrier_failures),
        )
    )

    if batch_id:
        query = query.where(Report.upload_batch_id == batch_id)

    result = await db.execute(query)
    reports = result.scalars().all()

    total_reports = len(reports)
    if total_reports == 0:
        return AccuracyReportResponse(
            batch_id=batch_id,
            batch_label=f"Batch {batch_id}" if batch_id else "Global Dataset",
            total_reports=0,
            labeled_reports_count=0,
            unlabeled_reports_count=0,
            overall_sif_accuracy=0.0,
            sif_metrics=compute_sif_metrics(0, 0, 0, 0),
            confusion_matrix=ConfusionMatrix(
                true_positives=0,
                false_positives=0,
                false_negatives=0,
                true_negatives=0,
                pending_evaluation=0,
            ),
            lsr_rule_accuracies=[],
            lsr_macro_accuracy=0.0,
            splits_breakdown={},
            evaluated_at=datetime.now(timezone.utc),
        )

    batch_label = reports[0].upload_batch_label if reports and reports[0].upload_batch_label else (f"Batch {batch_id}" if batch_id else "Global Dataset Benchmark")

    # Metrics aggregation by split
    split_counts: Dict[str, Dict[str, int]] = defaultdict(lambda: {"tp": 0, "fp": 0, "fn": 0, "tn": 0, "pending": 0, "lsr_correct": 0, "lsr_total": 0})
    lsr_rule_counts: Dict[str, Dict[str, int]] = defaultdict(lambda: {"total": 0, "correct": 0})

    labeled_count = 0
    unlabeled_count = 0

    for r in reports:
        gt_sif = r.ground_truth_sif_label
        gt_lsr = r.ground_truth_lsr
        split_name = (r.ground_truth_split or "unspecified").lower()

        if not gt_sif and not gt_lsr:
            unlabeled_count += 1
            continue

        labeled_count += 1

        # Evaluate SIF Classification
        if gt_sif:
            is_gt_sif = gt_sif in ["sif_potential", "sif", "true", "1"]
            pred_sif = r.sif_label

            if pred_sif is None:
                # Pending evaluation in async pipeline
                split_counts["overall"]["pending"] += 1
                split_counts[split_name]["pending"] += 1
            else:
                is_pred_sif = pred_sif == SIFLabel.sif_potential

                if is_gt_sif and is_pred_sif:
                    # True Positive
                    split_counts["overall"]["tp"] += 1
                    split_counts[split_name]["tp"] += 1
                elif not is_gt_sif and is_pred_sif:
                    # False Positive
                    split_counts["overall"]["fp"] += 1
                    split_counts[split_name]["fp"] += 1
                elif is_gt_sif and not is_pred_sif:
                    # False Negative
                    split_counts["overall"]["fn"] += 1
                    split_counts[split_name]["fn"] += 1
                else:
                    # True Negative
                    split_counts["overall"]["tn"] += 1
                    split_counts[split_name]["tn"] += 1

        # Evaluate LSR Tagging
        if gt_lsr:
            lsr_rule_counts[gt_lsr]["total"] += 1
            split_counts["overall"]["lsr_total"] += 1
            split_counts[split_name]["lsr_total"] += 1

            is_correct_lsr = match_lsr_rule(gt_lsr, r.primary_lsr, r.lsr_tags or [])
            if is_correct_lsr:
                lsr_rule_counts[gt_lsr]["correct"] += 1
                split_counts["overall"]["lsr_correct"] += 1
                split_counts[split_name]["lsr_correct"] += 1

    # Overall metrics
    overall_stats = split_counts["overall"]
    overall_metrics = compute_sif_metrics(
        overall_stats["tp"],
        overall_stats["fp"],
        overall_stats["fn"],
        overall_stats["tn"],
    )

    overall_cm = ConfusionMatrix(
        true_positives=overall_stats["tp"],
        false_positives=overall_stats["fp"],
        false_negatives=overall_stats["fn"],
        true_negatives=overall_stats["tn"],
        pending_evaluation=overall_stats["pending"],
    )

    # LSR Rule Accuracy list
    lsr_rule_accuracies: List[LSRRuleAccuracy] = []
    rule_acc_values: List[float] = []

    for rule_name, counts in sorted(lsr_rule_counts.items(), key=lambda x: -x[1]["total"]):
        tot = counts["total"]
        cor = counts["correct"]
        acc = round(cor / tot, 4) if tot > 0 else 0.0
        rule_acc_values.append(acc)
        lsr_rule_accuracies.append(
            LSRRuleAccuracy(
                rule=rule_name,
                total_ground_truth=tot,
                correct_predictions=cor,
                accuracy=acc,
            )
        )

    macro_lsr_acc = round(sum(rule_acc_values) / len(rule_acc_values), 4) if rule_acc_values else 0.0

    # Splits Breakdown
    splits_breakdown: Dict[str, SplitEvaluation] = {}
    for s_name, stats in split_counts.items():
        if s_name == "overall":
            continue
        s_metrics = compute_sif_metrics(stats["tp"], stats["fp"], stats["fn"], stats["tn"])
        s_cm = ConfusionMatrix(
            true_positives=stats["tp"],
            false_positives=stats["fp"],
            false_negatives=stats["fn"],
            true_negatives=stats["tn"],
            pending_evaluation=stats["pending"],
        )
        lsr_acc = round(stats["lsr_correct"] / stats["lsr_total"], 4) if stats["lsr_total"] > 0 else 0.0
        sample_count = stats["tp"] + stats["fp"] + stats["fn"] + stats["tn"] + stats["pending"]

        splits_breakdown[s_name] = SplitEvaluation(
            split=s_name,
            sample_count=sample_count,
            sif_metrics=s_metrics,
            confusion_matrix=s_cm,
            lsr_overall_accuracy=lsr_acc,
        )

    return AccuracyReportResponse(
        batch_id=batch_id,
        batch_label=batch_label,
        total_reports=total_reports,
        labeled_reports_count=labeled_count,
        unlabeled_reports_count=unlabeled_count,
        overall_sif_accuracy=overall_metrics.accuracy,
        sif_metrics=overall_metrics,
        confusion_matrix=overall_cm,
        lsr_rule_accuracies=lsr_rule_accuracies,
        lsr_macro_accuracy=macro_lsr_acc,
        splits_breakdown=splits_breakdown,
        evaluated_at=datetime.now(timezone.utc),
    )


async def list_all_batches(db: AsyncSession) -> BatchListResponse:
    """
    Lists all distinct uploaded dataset batches with their total and labeled report counts
    and evaluated accuracy summaries.
    """
    stmt = (
        select(
            Report.upload_batch_id,
            Report.upload_batch_label,
            func.count(Report.id).label("total_count"),
            func.min(Report.submitted_at).label("created_at"),
        )
        .where(Report.upload_batch_id.isnot(None))
        .group_by(Report.upload_batch_id, Report.upload_batch_label)
        .order_by(func.min(Report.submitted_at).desc())
    )

    results = (await db.execute(stmt)).all()
    batch_items: List[BatchSummaryItem] = []

    for row in results:
        b_id = row.upload_batch_id
        b_label = row.upload_batch_label or f"Batch {b_id}"
        total_count = row.total_count
        created_at = row.created_at

        # Fetch labeled count and evaluation
        labeled_count_stmt = (
            select(func.count(Report.id))
            .where(
                Report.upload_batch_id == b_id,
                (Report.ground_truth_sif_label.isnot(None) | Report.ground_truth_lsr.isnot(None)),
            )
        )
        labeled_count = (await db.execute(labeled_count_stmt)).scalar() or 0

        # Fetch distinct splits
        splits_stmt = (
            select(Report.ground_truth_split)
            .where(Report.upload_batch_id == b_id, Report.ground_truth_split.isnot(None))
            .distinct()
        )
        splits = [s for s in (await db.execute(splits_stmt)).scalars().all() if s]

        accuracy: Optional[float] = None
        f1: Optional[float] = None

        if labeled_count > 0:
            eval_res = await evaluate_batch_accuracy(db, batch_id=b_id)
            accuracy = eval_res.overall_sif_accuracy
            f1 = eval_res.sif_metrics.f1_score

        batch_items.append(
            BatchSummaryItem(
                batch_id=b_id,
                batch_label=b_label,
                total_reports=total_count,
                labeled_reports=labeled_count,
                sif_accuracy=accuracy,
                f1_score=f1,
                created_at=created_at,
                splits=splits,
            )
        )

    return BatchListResponse(
        total_batches=len(batch_items),
        batches=batch_items,
    )
