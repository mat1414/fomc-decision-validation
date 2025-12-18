"""
FOMC Decision Validation Tool

A Streamlit application for validating LLM-extracted policy decisions
from Federal Reserve FOMC meeting transcripts.
"""
import streamlit as st
import pandas as pd
import json
from datetime import datetime

from config import (
    TARGET_MEETINGS,
    SCORE_SCALE,
    DATA_PATHS,
    OCCURRENCE_OPTIONS,
    DECISION_TYPES,
    CONFIDENCE_LEVELS,
    ASSESSMENT_OPTIONS
)
from utils.data_loader import (
    load_transcripts_df,
    load_alternatives_df,
    load_transcript,
    load_alternatives,
    load_decisions,
    get_transcript_stats,
    search_transcript
)
from utils.export import (
    save_coding_results,
    export_to_csv,
    load_existing_results
)


# Page configuration
st.set_page_config(
    page_title="FOMC Decision Validation Tool",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="expanded"
)


def init_session_state():
    """Initialize session state variables."""
    if 'coder_id' not in st.session_state:
        st.session_state.coder_id = ""

    if 'selected_meeting' not in st.session_state:
        st.session_state.selected_meeting = None

    if 'decision_validations' not in st.session_state:
        st.session_state.decision_validations = {}

    if 'missing_decisions' not in st.session_state:
        st.session_state.missing_decisions = []

    if 'meeting_summary' not in st.session_state:
        st.session_state.meeting_summary = {
            'all_decisions_complete': False,
            'missing_check_complete': False,
            'overall_assessment': None,
            'general_notes': ''
        }

    if 'data_loaded' not in st.session_state:
        st.session_state.data_loaded = False


def reset_coding_state():
    """Reset coding state when meeting changes."""
    st.session_state.decision_validations = {}
    st.session_state.missing_decisions = []
    st.session_state.meeting_summary = {
        'all_decisions_complete': False,
        'missing_check_complete': False,
        'overall_assessment': None,
        'general_notes': ''
    }


def load_existing_coding():
    """Load existing coding results if available."""
    if st.session_state.coder_id and st.session_state.selected_meeting:
        existing = load_existing_results(
            st.session_state.selected_meeting,
            st.session_state.coder_id
        )
        if existing:
            # Restore decision validations
            for val in existing.get('decision_validations', []):
                idx = val.get('decision_index')
                if idx is not None:
                    st.session_state.decision_validations[idx] = val

            # Restore missing decisions
            st.session_state.missing_decisions = existing.get('missing_decisions', [])

            # Restore meeting summary
            st.session_state.meeting_summary = existing.get('meeting_summary', {
                'all_decisions_complete': False,
                'missing_check_complete': False,
                'overall_assessment': None,
                'general_notes': ''
            })
            return True
    return False


def get_validation_for_decision(decision_idx: int) -> dict:
    """Get or create validation dict for a decision."""
    if decision_idx not in st.session_state.decision_validations:
        st.session_state.decision_validations[decision_idx] = {
            'decision_index': decision_idx,
            'human_occurred': None,
            'human_corrected_description': None,
            'human_type_agree': None,
            'human_type_override': None,
            'human_score': None,
            'human_evidence': '',
            'human_notes': '',
            'human_confidence': None,
            'completed': False
        }
    return st.session_state.decision_validations[decision_idx]


def count_completed_decisions() -> int:
    """Count completed decision validations."""
    return sum(
        1 for v in st.session_state.decision_validations.values()
        if v.get('completed', False)
    )


def restore_from_uploaded_json(uploaded_file):
    """Restore coding progress from an uploaded JSON file."""
    try:
        content = uploaded_file.read().decode('utf-8')
        data = json.loads(content)

        # Extract metadata
        metadata = data.get('metadata', {})
        meeting_date = metadata.get('meeting_date')
        coder_id = metadata.get('coder_id')

        if not meeting_date or meeting_date not in TARGET_MEETINGS:
            return False, "Invalid or unsupported meeting date in file"

        # Set the coder ID and meeting
        st.session_state.coder_id = coder_id
        st.session_state.selected_meeting = meeting_date

        # Reset and restore decision validations
        st.session_state.decision_validations = {}
        for val in data.get('decision_validations', []):
            idx = val.get('decision_index')
            if idx is not None:
                st.session_state.decision_validations[idx] = val

        # Restore missing decisions
        st.session_state.missing_decisions = data.get('missing_decisions', [])

        # Restore meeting summary
        st.session_state.meeting_summary = data.get('meeting_summary', {
            'all_decisions_complete': False,
            'missing_check_complete': False,
            'overall_assessment': None,
            'general_notes': ''
        })

        return True, f"Restored progress for meeting {meeting_date}"

    except json.JSONDecodeError:
        return False, "Invalid JSON file"
    except Exception as e:
        return False, f"Error loading file: {str(e)}"


def render_sidebar():
    """Render the sidebar with coder ID, meeting selection, and progress."""
    with st.sidebar:
        st.header("Coder Identification")

        coder_id = st.text_input(
            "Coder ID",
            value=st.session_state.coder_id,
            placeholder="Enter your initials",
            help="Your unique identifier (e.g., initials)"
        )

        if coder_id != st.session_state.coder_id:
            st.session_state.coder_id = coder_id

        st.divider()

        # Resume previous work section
        st.header("Resume Previous Work")

        uploaded_file = st.file_uploader(
            "Upload saved progress (JSON)",
            type=['json'],
            help="Upload a previously downloaded JSON file to continue where you left off"
        )

        if uploaded_file is not None:
            if st.button("📂 Restore Progress", use_container_width=True):
                success, message = restore_from_uploaded_json(uploaded_file)
                if success:
                    st.success(message)
                    st.rerun()
                else:
                    st.error(message)

        st.divider()

        st.header("Meeting Selection")

        # Create meeting options
        meeting_options = {
            ymd: info['display_name']
            for ymd, info in TARGET_MEETINGS.items()
        }

        selected_display = st.selectbox(
            "Select Meeting",
            options=list(meeting_options.values()),
            index=None,
            placeholder="Choose a meeting to validate..."
        )

        # Find the ymd for selected meeting
        selected_ymd = None
        if selected_display:
            for ymd, display in meeting_options.items():
                if display == selected_display:
                    selected_ymd = ymd
                    break

        # Handle meeting change
        if selected_ymd != st.session_state.selected_meeting:
            st.session_state.selected_meeting = selected_ymd
            if selected_ymd:
                reset_coding_state()
                # Try to load existing results
                if load_existing_coding():
                    st.info("Loaded existing coding progress")

        st.divider()

        # Progress tracker
        if st.session_state.selected_meeting:
            st.header("Progress")

            decisions_df = load_decisions(st.session_state.selected_meeting)
            if decisions_df is not None:
                total_decisions = len(decisions_df)
                completed = count_completed_decisions()

                st.write(f"**Meeting:** {st.session_state.selected_meeting}")
                st.write(f"**Decisions:** {completed} of {total_decisions} validated")

                progress = completed / total_decisions if total_decisions > 0 else 0
                st.progress(progress)

                if completed == total_decisions:
                    st.success("All decisions validated!")
                else:
                    st.info("In Progress")

            st.divider()

            # Export buttons
            st.header("Download Results")

            if st.session_state.coder_id:
                json_data, json_filename = generate_results_json()
                csv_data, csv_filename = generate_results_csv()

                if json_data:
                    st.download_button(
                        label="📥 Download JSON",
                        data=json_data,
                        file_name=json_filename,
                        mime="application/json",
                        use_container_width=True
                    )

                if csv_data:
                    st.download_button(
                        label="📥 Download CSV",
                        data=csv_data,
                        file_name=csv_filename,
                        mime="text/csv",
                        use_container_width=True
                    )
            else:
                st.info("Enter Coder ID to enable downloads")


def generate_results_json():
    """Generate coding results as JSON string."""
    ymd = st.session_state.selected_meeting
    coder_id = st.session_state.coder_id

    decisions_df = load_decisions(ymd)
    if decisions_df is None:
        return None, None

    # Build decision validations list
    validations = []
    for idx, row in decisions_df.iterrows():
        val = get_validation_for_decision(idx).copy()
        val['claude_description'] = row['description']
        val['claude_type'] = row['type']
        val['claude_score'] = int(row['score'])
        val['claude_justification'] = row.get('justification', '')
        validations.append(val)

    # Get metadata
    transcripts_df = load_transcripts_df()
    stats = get_transcript_stats(ymd, transcripts_df)
    alternatives = load_alternatives(ymd, load_alternatives_df())

    output = {
        "metadata": {
            "meeting_date": ymd,
            "coder_id": coder_id,
            "coding_timestamp": datetime.now().isoformat(),
            "app_version": "1.0",
            "transcript_word_count": stats['word_count'],
            "num_decisions_claude": len(decisions_df),
            "alternatives_available": len(alternatives) > 0
        },
        "decision_validations": validations,
        "missing_decisions": st.session_state.missing_decisions,
        "meeting_summary": st.session_state.meeting_summary
    }

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"decisions_{ymd}_{coder_id}_{timestamp}.json"

    return json.dumps(output, indent=2, ensure_ascii=False), filename


def generate_results_csv():
    """Generate coding results as CSV string."""
    ymd = st.session_state.selected_meeting
    coder_id = st.session_state.coder_id

    decisions_df = load_decisions(ymd)
    if decisions_df is None:
        return None, None

    rows = []

    # Add validated decisions
    for idx, row in decisions_df.iterrows():
        val = get_validation_for_decision(idx)
        csv_row = {
            "meeting_date": ymd,
            "coder_id": coder_id,
            "coding_timestamp": datetime.now().isoformat(),
            "record_type": "validated_decision",
            "decision_index": val.get("decision_index"),
            "claude_description": row['description'],
            "claude_type": row['type'],
            "claude_score": int(row['score']),
            "claude_justification": row.get('justification', ''),
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
        rows.append(csv_row)

    # Add missing decisions
    for i, missing in enumerate(st.session_state.missing_decisions):
        csv_row = {
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
        rows.append(csv_row)

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
        "human_notes": st.session_state.meeting_summary.get("general_notes"),
        "human_confidence": st.session_state.meeting_summary.get("overall_assessment"),
        "completed": st.session_state.meeting_summary.get("all_decisions_complete")
    }
    rows.append(summary_row)

    df = pd.DataFrame(rows)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"decisions_{ymd}_{coder_id}_{timestamp}.csv"

    return df.to_csv(index=False), filename


def render_meeting_overview(ymd: str, decisions_df: pd.DataFrame):
    """Render the meeting overview section."""
    meeting_info = TARGET_MEETINGS[ymd]
    transcripts_df = load_transcripts_df()
    stats = get_transcript_stats(ymd, transcripts_df)
    alternatives = load_alternatives(ymd, load_alternatives_df())

    st.markdown("---")
    st.header(f"MEETING: {meeting_info['display_name']}")
    st.markdown("---")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Decisions Identified", len(decisions_df))

    with col2:
        st.metric("Transcript Length", f"~{stats['word_count']:,} words")

    with col3:
        alt_status = f"Yes ({len(alternatives)})" if alternatives else "No"
        st.metric("Policy Alternatives", alt_status)


def render_alternatives_section(ymd: str):
    """Render the policy alternatives expander."""
    alternatives_df = load_alternatives_df()
    alternatives = load_alternatives(ymd, alternatives_df)

    with st.expander("📋 View Policy Alternatives", expanded=False):
        if not alternatives:
            st.info(
                "No policy alternatives data available for this meeting.\n\n"
                "(This was an emergency meeting with a non-standard format.)"
            )
        else:
            for alt in alternatives:
                st.markdown("---")
                st.subheader(alt['label'])

                st.markdown("**Description:**")
                st.write(alt['description'])

                st.markdown("**Statement:**")
                with st.container():
                    st.text_area(
                        f"Statement for {alt['label']}",
                        value=alt['statement'],
                        height=150,
                        disabled=True,
                        label_visibility="collapsed"
                    )


def render_transcript_section(ymd: str):
    """Render the transcript viewer expander."""
    transcripts_df = load_transcripts_df()

    with st.expander("📄 View Full Transcript", expanded=False):
        # Search functionality
        search_term = st.text_input(
            "Search transcript",
            placeholder="Enter search term...",
            key="transcript_search"
        )

        transcript_text = load_transcript(ymd, transcripts_df)

        if search_term:
            results = search_transcript(transcript_text, search_term)
            st.write(f"Found {len(results)} matches for '{search_term}'")

            if results:
                for result in results[:50]:  # Limit to first 50 results
                    # Highlight the search term
                    highlighted = result['text'].replace(
                        search_term,
                        f"**{search_term}**"
                    )
                    st.markdown(f"---\n{highlighted}")
        else:
            # Show full transcript in scrollable container
            st.text_area(
                "Full Transcript",
                value=transcript_text,
                height=500,
                disabled=True,
                label_visibility="collapsed"
            )


def render_decision_validation(idx: int, row: pd.Series, total_decisions: int):
    """Render validation form for a single decision."""
    validation = get_validation_for_decision(idx)

    # Decision header
    st.markdown("---")
    status_icon = "✅" if validation.get('completed') else "⬜"
    st.subheader(f"{status_icon} Decision {idx + 1} of {total_decisions}")

    # Claude's extraction
    st.markdown("#### Claude's Extraction")

    with st.container():
        st.markdown("**Description:**")
        st.info(row['description'])

        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"**Type:** `{row['type']}`")
        with col2:
            score = int(row['score'])
            score_label = SCORE_SCALE.get(score, "Unknown")
            st.markdown(f"**Score:** `{score}` ({score_label})")

        if pd.notna(row.get('justification')):
            st.markdown("**Justification:**")
            st.caption(row['justification'])

    st.markdown("#### Your Validation")

    # 1. Did this decision occur?
    st.markdown("**1. Did this decision occur at this meeting?**")

    occurred_options = list(OCCURRENCE_OPTIONS.values())
    occurred_keys = list(OCCURRENCE_OPTIONS.keys())

    current_occurred_idx = None
    if validation.get('human_occurred') in occurred_keys:
        current_occurred_idx = occurred_keys.index(validation['human_occurred'])

    occurred_selection = st.radio(
        f"Occurred_{idx}",
        options=occurred_options,
        index=current_occurred_idx,
        key=f"occurred_{idx}",
        label_visibility="collapsed"
    )

    if occurred_selection:
        validation['human_occurred'] = occurred_keys[occurred_options.index(occurred_selection)]

    # Show correction field if needed
    if validation.get('human_occurred') == 'yes_corrected':
        validation['human_corrected_description'] = st.text_area(
            "Corrected description",
            value=validation.get('human_corrected_description', ''),
            key=f"corrected_desc_{idx}",
            placeholder="Enter the corrected description..."
        )

    # 2. Type classification
    st.markdown("**2. Type classification:**")

    type_agree = st.radio(
        f"Type agreement_{idx}",
        options=[f"Agree: {row['type']}", "Disagree"],
        index=0 if validation.get('human_type_agree', True) else 1,
        key=f"type_agree_{idx}",
        label_visibility="collapsed"
    )

    validation['human_type_agree'] = type_agree.startswith("Agree")

    if not validation['human_type_agree']:
        validation['human_type_override'] = st.selectbox(
            "Should be:",
            options=DECISION_TYPES,
            key=f"type_override_{idx}"
        )
    else:
        validation['human_type_override'] = None

    # 3. Policy stance score
    st.markdown("**3. Policy stance score:**")

    st.caption(f"Claude's score: **{int(row['score'])}**")

    # Score reference
    with st.expander("Score scale reference", expanded=False):
        for score_val, score_desc in SCORE_SCALE.items():
            st.write(f"`{score_val:+d}`: {score_desc}")

    current_score = validation.get('human_score')
    if current_score is None:
        current_score = int(row['score'])

    validation['human_score'] = st.slider(
        "Your score",
        min_value=-3,
        max_value=3,
        value=current_score,
        key=f"score_{idx}",
        format="%+d"
    )

    # 4. Evidence location
    st.markdown("**4. Evidence location:**")
    validation['human_evidence'] = st.text_area(
        "Where in the transcript is this decision documented?",
        value=validation.get('human_evidence', ''),
        key=f"evidence_{idx}",
        placeholder="Paste relevant excerpt or describe location...",
        label_visibility="collapsed"
    )

    # 5. Notes
    st.markdown("**5. Notes (optional):**")
    validation['human_notes'] = st.text_area(
        "Any concerns, ambiguities, etc.",
        value=validation.get('human_notes', ''),
        key=f"notes_{idx}",
        placeholder="Optional notes...",
        label_visibility="collapsed"
    )

    # 6. Confidence
    st.markdown("**6. Confidence:**")

    confidence_idx = None
    if validation.get('human_confidence') in CONFIDENCE_LEVELS:
        confidence_idx = CONFIDENCE_LEVELS.index(validation['human_confidence'])

    confidence_selection = st.radio(
        f"Confidence_{idx}",
        options=["High confidence", "Medium confidence", "Low confidence / uncertain"],
        index=confidence_idx,
        key=f"confidence_{idx}",
        label_visibility="collapsed",
        horizontal=True
    )

    if confidence_selection:
        validation['human_confidence'] = CONFIDENCE_LEVELS[
            ["High confidence", "Medium confidence", "Low confidence / uncertain"].index(confidence_selection)
        ]

    # Mark complete button
    col1, col2 = st.columns([1, 4])
    with col1:
        if st.button(
            "✓ Mark Complete" if not validation.get('completed') else "✓ Completed",
            key=f"complete_{idx}",
            type="primary" if not validation.get('completed') else "secondary"
        ):
            # Validate required fields
            if validation.get('human_occurred') is None:
                st.error("Please indicate if this decision occurred")
            elif validation.get('human_confidence') is None:
                st.error("Please select a confidence level")
            else:
                validation['completed'] = True
                st.success("Decision marked as complete!")
                st.rerun()

    with col2:
        if st.button("Clear Responses", key=f"clear_{idx}"):
            st.session_state.decision_validations[idx] = {
                'decision_index': idx,
                'human_occurred': None,
                'human_corrected_description': None,
                'human_type_agree': None,
                'human_type_override': None,
                'human_score': None,
                'human_evidence': '',
                'human_notes': '',
                'human_confidence': None,
                'completed': False
            }
            st.rerun()

    # Update session state
    st.session_state.decision_validations[idx] = validation


def render_missing_decisions_section():
    """Render the missing decisions check section."""
    st.markdown("---")
    st.header("Missing Decisions Check")
    st.markdown("---")

    st.markdown(
        "Did the committee make any significant policy decisions that "
        "Claude did **NOT** identify?"
    )

    has_missing = st.radio(
        "Missing decisions check",
        options=["No, Claude captured all major decisions", "Yes, there are missing decisions"],
        key="has_missing_decisions",
        label_visibility="collapsed"
    )

    if has_missing == "Yes, there are missing decisions":
        st.markdown("### Add Missing Decisions")

        # Show existing missing decisions
        for i, missing in enumerate(st.session_state.missing_decisions):
            with st.expander(f"Missing Decision #{i+1}", expanded=True):
                missing['description'] = st.text_area(
                    "Description",
                    value=missing.get('description', ''),
                    key=f"missing_desc_{i}"
                )
                missing['type'] = st.selectbox(
                    "Type",
                    options=DECISION_TYPES,
                    key=f"missing_type_{i}"
                )
                missing['score'] = st.slider(
                    "Your score",
                    min_value=-3,
                    max_value=3,
                    value=missing.get('score', 0),
                    key=f"missing_score_{i}",
                    format="%+d"
                )
                missing['evidence'] = st.text_area(
                    "Evidence",
                    value=missing.get('evidence', ''),
                    key=f"missing_evidence_{i}"
                )

                if st.button(f"Remove Missing Decision #{i+1}", key=f"remove_missing_{i}"):
                    st.session_state.missing_decisions.pop(i)
                    st.rerun()

        # Add new missing decision button
        if st.button("+ Add Another Missing Decision"):
            st.session_state.missing_decisions.append({
                'description': '',
                'type': 'other',
                'score': 0,
                'evidence': ''
            })
            st.rerun()

    st.session_state.meeting_summary['missing_check_complete'] = True


def render_meeting_summary_section(decisions_df: pd.DataFrame):
    """Render the meeting-level summary section."""
    st.markdown("---")
    st.header("Meeting Validation Summary")
    st.markdown("---")

    total = len(decisions_df)
    completed = count_completed_decisions()
    missing_count = len(st.session_state.missing_decisions)

    col1, col2 = st.columns(2)
    with col1:
        st.metric("Decisions validated", f"{completed} of {total}")
    with col2:
        st.metric("Missing decisions identified", missing_count)

    st.markdown("**Overall assessment of Claude's decision extraction for this meeting:**")

    assessment_options = list(ASSESSMENT_OPTIONS.values())
    assessment_keys = list(ASSESSMENT_OPTIONS.keys())

    current_assessment_idx = None
    if st.session_state.meeting_summary.get('overall_assessment') in assessment_keys:
        current_assessment_idx = assessment_keys.index(
            st.session_state.meeting_summary['overall_assessment']
        )

    assessment_selection = st.radio(
        "Overall assessment",
        options=assessment_options,
        index=current_assessment_idx,
        key="overall_assessment",
        label_visibility="collapsed"
    )

    if assessment_selection:
        st.session_state.meeting_summary['overall_assessment'] = assessment_keys[
            assessment_options.index(assessment_selection)
        ]

    st.markdown("**General notes on this meeting's coding:**")
    st.session_state.meeting_summary['general_notes'] = st.text_area(
        "General notes",
        value=st.session_state.meeting_summary.get('general_notes', ''),
        key="general_notes",
        placeholder="Any overall observations about the coding quality...",
        label_visibility="collapsed"
    )

    # Check if all decisions complete
    st.session_state.meeting_summary['all_decisions_complete'] = (completed == total)

    # Submit section
    st.markdown("---")
    st.subheader("📤 Submit & Download Results")

    # Validation checks
    ready_to_submit = True
    if not st.session_state.coder_id:
        st.error("Please enter your Coder ID in the sidebar")
        ready_to_submit = False
    elif completed < total:
        st.warning(f"Only {completed} of {total} decisions validated. Please complete all decisions.")
        ready_to_submit = False
    elif st.session_state.meeting_summary.get('overall_assessment') is None:
        st.error("Please select an overall assessment above")
        ready_to_submit = False

    if ready_to_submit:
        st.success("✅ All validations complete! Download your results below:")

        json_data, json_filename = generate_results_json()
        csv_data, csv_filename = generate_results_csv()

        col1, col2 = st.columns(2)

        with col1:
            if json_data:
                st.download_button(
                    label="📥 Download JSON",
                    data=json_data,
                    file_name=json_filename,
                    mime="application/json",
                    use_container_width=True,
                    type="primary"
                )

        with col2:
            if csv_data:
                st.download_button(
                    label="📥 Download CSV",
                    data=csv_data,
                    file_name=csv_filename,
                    mime="text/csv",
                    use_container_width=True,
                    type="primary"
                )

        st.balloons()


def main():
    """Main application entry point."""
    init_session_state()

    # Title
    st.title("🏛️ FOMC Decision Validation Tool")

    # Render sidebar
    render_sidebar()

    # Main content
    if not st.session_state.coder_id:
        st.warning("Please enter your Coder ID in the sidebar to begin.")
        return

    if not st.session_state.selected_meeting:
        st.info("Please select a meeting from the sidebar to begin validation.")

        # Show overview of target meetings
        st.markdown("### Available Meetings for Validation")

        for ymd, info in TARGET_MEETINGS.items():
            decisions_df = load_decisions(ymd)
            n_decisions = len(decisions_df) if decisions_df is not None else "?"
            alt_status = "Yes" if info['has_alternatives'] else "No"

            st.markdown(
                f"- **{info['display_name']}**\n"
                f"  - Era: {info['era']}\n"
                f"  - Decisions: {n_decisions}\n"
                f"  - Alternatives available: {alt_status}"
            )
        return

    # Load data for selected meeting
    ymd = st.session_state.selected_meeting
    decisions_df = load_decisions(ymd)

    if decisions_df is None:
        st.error(f"Could not load decisions for meeting {ymd}")
        return

    # Render meeting overview
    render_meeting_overview(ymd, decisions_df)

    # Render policy alternatives
    render_alternatives_section(ymd)

    # Render transcript viewer
    render_transcript_section(ymd)

    # Render decision validations
    st.markdown("---")
    st.header("Decision-by-Decision Validation")

    # Use tabs for decisions
    decision_tabs = st.tabs([
        f"Decision {i+1}" + (" ✓" if get_validation_for_decision(i).get('completed') else "")
        for i in range(len(decisions_df))
    ])

    for idx, (tab, (_, row)) in enumerate(zip(decision_tabs, decisions_df.iterrows())):
        with tab:
            render_decision_validation(idx, row, len(decisions_df))

    # Render missing decisions section
    render_missing_decisions_section()

    # Render meeting summary
    render_meeting_summary_section(decisions_df)


if __name__ == "__main__":
    main()
