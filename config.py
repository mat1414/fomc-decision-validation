# Configuration for FOMC Decision Validation Tool

# Target meetings for validation
TARGET_MEETINGS = {
    "19791006": {
        "display_name": "October 6, 1979 (Volcker's Saturday Night Special)",
        "era": "Volcker",
        "has_alternatives": False
    },
    "19940816": {
        "display_name": "August 16, 1994 (Greenspan tightening cycle)",
        "era": "Greenspan",
        "has_alternatives": True
    },
    "20081216": {
        "display_name": "December 16, 2008 (Financial crisis ZLB)",
        "era": "Bernanke",
        "has_alternatives": True
    },
    "20110809": {
        "display_name": "August 9, 2011 (Extended period debate)",
        "era": "Bernanke",
        "has_alternatives": True
    },
    "20190731": {
        "display_name": "July 31, 2019 (Powell mid-cycle cut)",
        "era": "Powell",
        "has_alternatives": True
    }
}

# Score scale definitions
SCORE_SCALE = {
    -3: "Strongly dovish (maximum accommodation)",
    -2: "Moderately dovish",
    -1: "Slightly dovish",
    0: "Neutral",
    1: "Slightly hawkish",
    2: "Moderately hawkish",
    3: "Strongly hawkish (maximum tightening)"
}

# Data paths
DATA_PATHS = {
    "transcripts": "data/transcripts.parquet",
    "alternatives": "data/alternatives.pkl",
    "decisions_dir": "data/decisions/",
    "results_dir": "data/coding_results/"
}

# Decision occurrence options
OCCURRENCE_OPTIONS = {
    "yes_exact": "Yes, exactly as described",
    "yes_corrected": "Yes, but description needs correction",
    "no": "No, this did not happen"
}

# Decision type options
DECISION_TYPES = ["rate decision", "communication", "other"]

# Confidence levels
CONFIDENCE_LEVELS = ["high", "medium", "low"]

# Overall assessment options
ASSESSMENT_OPTIONS = {
    "excellent": "Excellent (all decisions correct, scores accurate)",
    "good": "Good (minor issues only)",
    "fair": "Fair (some errors but mostly correct)",
    "poor": "Poor (significant errors or omissions)"
}
