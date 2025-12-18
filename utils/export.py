"""
Export utilities for FOMC Decision Validation Tool.
"""
import json
import pandas as pd
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional, List
import os

from config import DATA_PATHS


def get_results_filename(ymd: str, coder_id: str, extension: str = "json") -> str:
    """
    Generate a filename for coding results.

    Args:
        ymd: Meeting date
        coder_id: Coder identifier
        extension: File extension (json or csv)

    Returns:
        Filename string.
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"decisions_{ymd}_{coder_id}_{timestamp}.{extension}"


def save_coding_results(
    ymd: str,
    coder_id: str,
    decision_validations: List[Dict],
    missing_decisions: List[Dict],
    meeting_summary: Dict,
    metadata: Dict
) -> str:
    """
    Save coding results to JSON file.

    Args:
        ymd: Meeting date
        coder_id: Coder identifier
        decision_validations: List of validation dicts for each decision
        missing_decisions: List of missing decision dicts
        meeting_summary: Summary dict with overall assessment
        metadata: Metadata dict

    Returns:
        Path to saved file.
    """
    results_dir = Path(DATA_PATHS["results_dir"])
    results_dir.mkdir(parents=True, exist_ok=True)

    filename = get_results_filename(ymd, coder_id, "json")
    filepath = results_dir / filename

    output = {
        "metadata": {
            "meeting_date": ymd,
            "coder_id": coder_id,
            "coding_timestamp": datetime.now().isoformat(),
            "app_version": "1.0",
            **metadata
        },
        "decision_validations": decision_validations,
        "missing_decisions": missing_decisions,
        "meeting_summary": meeting_summary
    }

    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    return str(filepath)


def export_to_csv(
    ymd: str,
    coder_id: str,
    decision_validations: List[Dict],
    missing_decisions: List[Dict],
    meeting_summary: Dict
) -> str:
    """
    Export coding results to CSV file (flattened format).

    Args:
        ymd: Meeting date
        coder_id: Coder identifier
        decision_validations: List of validation dicts
        missing_decisions: List of missing decision dicts
        meeting_summary: Summary dict

    Returns:
        Path to saved file.
    """
    results_dir = Path(DATA_PATHS["results_dir"])
    results_dir.mkdir(parents=True, exist_ok=True)

    filename = get_results_filename(ymd, coder_id, "csv")
    filepath = results_dir / filename

    rows = []

    # Add validated decisions
    for val in decision_validations:
        row = {
            "meeting_date": ymd,
            "coder_id": coder_id,
            "coding_timestamp": datetime.now().isoformat(),
            "record_type": "validated_decision",
            "decision_index": val.get("decision_index"),
            "claude_description": val.get("claude_description"),
            "claude_type": val.get("claude_type"),
            "claude_score": val.get("claude_score"),
            "claude_justification": val.get("claude_justification"),
            "human_occurred": val.get("human_occurred"),
            "human_corrected_description": val.get("human_corrected_description"),
            "human_type_agree": val.get("human_type_agree"),
            "human_type_override": val.get("human_type_override"),
            "human_score": val.get("human_score"),
            "human_evidence": val.get("human_evidence"),
            "human_notes": val.get("human_notes"),
            "human_confidence": val.get("human_confidence"),
            "completed": val.get("completed")
        }
        rows.append(row)

    # Add missing decisions
    for i, missing in enumerate(missing_decisions):
        row = {
            "meeting_date": ymd,
            "coder_id": coder_id,
            "coding_timestamp": datetime.now().isoformat(),
            "record_type": "missing_decision",
            "decision_index": f"missing_{i+1}",
            "claude_description": None,
            "claude_type": None,
            "claude_score": None,
            "claude_justification": None,
            "human_occurred": "missing",
            "human_corrected_description": missing.get("description"),
            "human_type_agree": None,
            "human_type_override": missing.get("type"),
            "human_score": missing.get("score"),
            "human_evidence": missing.get("evidence"),
            "human_notes": missing.get("notes"),
            "human_confidence": missing.get("confidence"),
            "completed": True
        }
        rows.append(row)

    # Add summary row
    summary_row = {
        "meeting_date": ymd,
        "coder_id": coder_id,
        "coding_timestamp": datetime.now().isoformat(),
        "record_type": "meeting_summary",
        "decision_index": None,
        "claude_description": None,
        "claude_type": None,
        "claude_score": None,
        "claude_justification": None,
        "human_occurred": None,
        "human_corrected_description": None,
        "human_type_agree": None,
        "human_type_override": None,
        "human_score": None,
        "human_evidence": None,
        "human_notes": meeting_summary.get("general_notes"),
        "human_confidence": meeting_summary.get("overall_assessment"),
        "completed": meeting_summary.get("all_decisions_complete")
    }
    rows.append(summary_row)

    df = pd.DataFrame(rows)
    df.to_csv(filepath, index=False)

    return str(filepath)


def load_existing_results(ymd: str, coder_id: str) -> Optional[Dict]:
    """
    Load the most recent existing results for a meeting/coder combination.

    Args:
        ymd: Meeting date
        coder_id: Coder identifier

    Returns:
        Results dict if found, None otherwise.
    """
    results_dir = Path(DATA_PATHS["results_dir"])

    if not results_dir.exists():
        return None

    # Find matching files
    pattern = f"decisions_{ymd}_{coder_id}_*.json"
    matching_files = list(results_dir.glob(pattern))

    if not matching_files:
        return None

    # Get most recent
    most_recent = max(matching_files, key=lambda p: p.stat().st_mtime)

    with open(most_recent, 'r', encoding='utf-8') as f:
        return json.load(f)


def list_existing_results(coder_id: Optional[str] = None) -> List[Dict]:
    """
    List all existing result files.

    Args:
        coder_id: Optional filter by coder ID

    Returns:
        List of dicts with file info.
    """
    results_dir = Path(DATA_PATHS["results_dir"])

    if not results_dir.exists():
        return []

    results = []
    for filepath in results_dir.glob("decisions_*.json"):
        parts = filepath.stem.split("_")
        if len(parts) >= 4:
            file_ymd = parts[1]
            file_coder = parts[2]

            if coder_id and file_coder != coder_id:
                continue

            results.append({
                "filename": filepath.name,
                "meeting_date": file_ymd,
                "coder_id": file_coder,
                "modified": datetime.fromtimestamp(filepath.stat().st_mtime).isoformat()
            })

    return sorted(results, key=lambda x: x["modified"], reverse=True)
