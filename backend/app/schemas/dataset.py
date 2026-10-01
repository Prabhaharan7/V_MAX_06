"""
================================================================================
SIF Sentinel AI - Dataset & Accuracy Benchmark Schemas
SIH 2026 Problem Statement PS 26165 (Oil India Limited)
================================================================================
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class SIFMetrics(BaseModel):
    accuracy: float = Field(..., description="Overall SIF accuracy (TP+TN)/(Total)")
    precision: float = Field(..., description="Precision for SIF-Potential class TP/(TP+FP)")
    recall: float = Field(..., description="Recall / Sensitivity for SIF-Potential class TP/(TP+FN)")
    f1_score: float = Field(..., description="Harmonic mean of precision and recall")
    specificity: float = Field(..., description="True negative rate TN/(TN+FP)")
    total_evaluated: int = Field(..., description="Number of evaluated samples")
    sif_count: int = Field(..., description="Ground truth SIF potential count")
    non_sif_count: int = Field(..., description="Ground truth Non-SIF count")


class ConfusionMatrix(BaseModel):
    true_positives: int = Field(..., description="Actual SIF-Potential, Model Predicted SIF-Potential")
    false_positives: int = Field(..., description="Actual Non-SIF, Model Predicted SIF-Potential")
    false_negatives: int = Field(..., description="Actual SIF-Potential, Model Predicted Non-SIF")
    true_negatives: int = Field(..., description="Actual Non-SIF, Model Predicted Non-SIF")
    pending_evaluation: int = Field(default=0, description="Reports awaiting background AI classification")


class LSRRuleAccuracy(BaseModel):
    rule: str = Field(..., description="Life-Saving Rule name")
    total_ground_truth: int = Field(..., description="Total ground truth occurrences")
    correct_predictions: int = Field(..., description="Correctly tagged occurrences by model")
    accuracy: float = Field(..., description="Rule-level accuracy / recall percentage")


class SplitEvaluation(BaseModel):
    split: str = Field(..., description="Data split: train, test, val, or overall")
    sample_count: int = Field(..., description="Number of ground-truth labeled reports in this split")
    sif_metrics: SIFMetrics
    confusion_matrix: ConfusionMatrix
    lsr_overall_accuracy: float = Field(..., description="Micro-average LSR tagging accuracy in this split")


class AccuracyReportResponse(BaseModel):
    batch_id: Optional[str] = None
    batch_label: Optional[str] = None
    total_reports: int = Field(..., description="Total reports in this batch or overall")
    labeled_reports_count: int = Field(..., description="Reports containing ground-truth annotations")
    unlabeled_reports_count: int = Field(..., description="Reports without ground-truth labels")
    overall_sif_accuracy: float = Field(..., description="Overall SIF classification accuracy")
    sif_metrics: SIFMetrics
    confusion_matrix: ConfusionMatrix
    lsr_rule_accuracies: List[LSRRuleAccuracy] = []
    lsr_macro_accuracy: float = Field(..., description="Macro-average accuracy across all Life-Saving Rules")
    splits_breakdown: Dict[str, SplitEvaluation] = {}
    evaluated_at: datetime = Field(default_factory=datetime.utcnow)


class BatchSummaryItem(BaseModel):
    batch_id: str
    batch_label: str
    total_reports: int
    labeled_reports: int
    sif_accuracy: Optional[float] = None
    f1_score: Optional[float] = None
    created_at: Optional[datetime] = None
    splits: List[str] = []


class BatchListResponse(BaseModel):
    total_batches: int
    batches: List[BatchSummaryItem]
