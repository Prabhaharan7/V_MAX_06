import logging
from app.ml.sif_classifier import classify_report
from app.ml.lsr_tagger import tag_report
from app.ml.barrier_extractor import extract_barriers_for_report

logger = logging.getLogger("sif_sentinel.nlp_pipeline")


async def process_report_nlp_pipeline(report_id: int) -> None:
    """
    Executes the Complete AI/NLP Pipeline in a Background Task:
    1. Hybrid SIF-Potential Classification (spaCy rules + sentence-transformers semantic layer + triage)
    2. Multi-Label IOGP Life-Saving Rules Tagging (tag_report: PhraseMatcher + canonical cosine fallback)
    3. Safety Barrier Failure Extraction (extract_barriers_for_report: 10-category taxonomy + evidence phrases + severity)
    """
    logger.info(f"Step 1/3: Running Hybrid SIF Classification for Report ID {report_id}...")
    await classify_report(report_id)

    logger.info(f"Step 2/3: Running IOGP Multi-Label LSR Tagging for Report ID {report_id}...")
    await tag_report(report_id)

    logger.info(f"Step 3/3: Running Safety Barrier Failure Extraction for Report ID {report_id}...")
    await extract_barriers_for_report(report_id)

    logger.info(f"Background NLP pipeline successfully completed for Report ID {report_id}.")

