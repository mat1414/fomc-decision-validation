"""
Data loading utilities for FOMC Decision Validation Tool.
"""
import pandas as pd
import pickle
from pathlib import Path
from typing import List, Dict, Optional
import streamlit as st

from config import DATA_PATHS


@st.cache_data
def load_transcripts_df() -> pd.DataFrame:
    """
    Load the full transcripts DataFrame from parquet file.
    Cached to avoid reloading on each Streamlit rerun.
    """
    return pd.read_parquet(DATA_PATHS["transcripts"])


@st.cache_data
def load_alternatives_df() -> pd.DataFrame:
    """
    Load the full alternatives DataFrame from pickle file.
    Cached to avoid reloading on each Streamlit rerun.
    """
    with open(DATA_PATHS["alternatives"], 'rb') as f:
        return pickle.load(f)


def load_transcript(ymd: str, transcripts_df: pd.DataFrame) -> str:
    """
    Filter transcripts DataFrame to a single meeting and reconstruct full text.

    Args:
        ymd: Meeting date as string (e.g., "20100127")
        transcripts_df: Full transcripts DataFrame

    Returns:
        Formatted string with speaker labels and their utterances.
    """
    meeting_df = transcripts_df[transcripts_df['ymd'] == ymd].sort_values('n')

    if len(meeting_df) == 0:
        return f"No transcript found for meeting {ymd}"

    lines = []
    for _, row in meeting_df.iterrows():
        # Build speaker label from title and name
        title = str(row['titletidy']).strip() if pd.notna(row['titletidy']) else ""
        speaker = str(row['stablespeaker']).strip() if pd.notna(row['stablespeaker']) else ""

        # Format speaker label
        if title and speaker:
            if title.upper() in ['CHAIR', 'CHAIRMAN', 'VICE CHAIR', 'VICE CHAIRMAN']:
                speaker_label = f"{title.upper()} {speaker}"
            else:
                speaker_label = f"{title.upper()}. {speaker}"
        elif speaker:
            speaker_label = speaker
        else:
            speaker_label = "UNKNOWN"

        # Get the text
        text = str(row['combined']).strip() if pd.notna(row['combined']) else ""

        if text:
            lines.append(f"{speaker_label}: {text}")

    return "\n\n".join(lines)


def load_transcript_df(ymd: str, transcripts_df: pd.DataFrame) -> pd.DataFrame:
    """
    Get the transcript DataFrame for a single meeting.

    Args:
        ymd: Meeting date as string
        transcripts_df: Full transcripts DataFrame

    Returns:
        Filtered and sorted DataFrame for the meeting.
    """
    return transcripts_df[transcripts_df['ymd'] == ymd].sort_values('n').copy()


def get_transcript_stats(ymd: str, transcripts_df: pd.DataFrame) -> Dict:
    """
    Get statistics about a meeting's transcript.

    Args:
        ymd: Meeting date as string
        transcripts_df: Full transcripts DataFrame

    Returns:
        Dictionary with word count and utterance count.
    """
    meeting_df = transcripts_df[transcripts_df['ymd'] == ymd]
    return {
        "word_count": int(meeting_df['words'].sum()),
        "utterance_count": len(meeting_df)
    }


def load_alternatives(ymd: str, alternatives_df: pd.DataFrame) -> List[Dict]:
    """
    Get policy alternatives for a meeting.

    Args:
        ymd: Meeting date as string
        alternatives_df: Full alternatives DataFrame

    Returns:
        List of dicts with keys: label, description, statement.
        Returns empty list if no alternatives exist.
    """
    meeting_alts = alternatives_df[alternatives_df['ymd'] == ymd]

    if len(meeting_alts) == 0:
        return []

    return meeting_alts[['label', 'description', 'statement']].to_dict('records')


def load_decisions(ymd: str) -> Optional[pd.DataFrame]:
    """
    Load Claude's extracted decisions for a meeting from CSV.

    Args:
        ymd: Meeting date as string

    Returns:
        DataFrame with decisions, or None if file doesn't exist.
    """
    path = Path(DATA_PATHS["decisions_dir"]) / f"adopted_decisions_{ymd}.csv"

    if not path.exists():
        return None

    df = pd.read_csv(path)

    # Ensure required columns exist
    required_cols = ['description', 'type', 'score', 'justification']
    for col in required_cols:
        if col not in df.columns:
            df[col] = None

    return df


def search_transcript(transcript_text: str, search_term: str) -> List[Dict]:
    """
    Search transcript for a term and return matching excerpts.

    Args:
        transcript_text: Full transcript as string
        search_term: Term to search for (case-insensitive)

    Returns:
        List of dicts with matching excerpts and context.
    """
    if not search_term:
        return []

    results = []
    search_lower = search_term.lower()

    # Split into utterances
    utterances = transcript_text.split("\n\n")

    for i, utterance in enumerate(utterances):
        if search_lower in utterance.lower():
            results.append({
                "index": i,
                "text": utterance,
                "preview": utterance[:200] + "..." if len(utterance) > 200 else utterance
            })

    return results
