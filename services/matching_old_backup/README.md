# RIQ LabMatch - Matching Service V3

Sophisticated multi-stage matching algorithm for matching students to faculty research labs.

## Features

- **Multi-stage filtering**: Fast keyword filter → Embedding similarity → Detailed scoring
- **LLM-powered extraction**: Intelligent student profile extraction from resumes
- **Semantic understanding**: Uses OpenAI embeddings for semantic similarity
- **Comprehensive scoring**: 6-component scoring system (keyword, semantic, domain, technique, experience, activity)
- **Personalized explanations**: LLM-generated match explanations and approach suggestions
- **User preferences**: Collects and uses student preferences for better matching
- **Fast mode**: Keyword-only matching for quick results (~50ms)

## Architecture

```
Stage 1: Fast keyword filter (100ms) → Top 100 candidates
Stage 2: Embedding similarity (500ms) → Top 30 candidates  
Stage 3: LLM reasoning (2-3s) → Top 20 with explanations
```

**Cost**: ~$0.01-0.02 per match request (mostly Stage 3)  
**Speed**: ~3-5 seconds total

## Installation

```bash
pip install -r requirements.txt
```

Set your OpenAI API key:
```bash
export OPENAI_API_KEY='your-key-here'
```

## Quick Start

### Basic Usage

```python
from services.matching import SophisticatedMatcher

# Initialize matcher
matcher = SophisticatedMatcher(
    faculty_data_path="faculty_pipeline/output/harvard_university_20260120_162804.json",
    precompute_embeddings=True,
)

# Match student to faculty
results = matcher.match(
    resume_text="Your resume text here...",
    user_interests=["machine learning", "AI"],
    user_techniques=["Python", "TensorFlow"],
    top_k=20,
)

# Access results
for match in results['matches']:
    print(f"{match['name']}: {match['total_score']:.1f}/100")
```

### With User Preferences

```python
from services.matching.user_preferences import UserPreferences

preferences = UserPreferences(
    research_interests=["genetics", "genomics"],
    techniques=["PCR", "cell culture"],
    experience_level="undergraduate",
    lab_type_preference="wet",
    funding_required=True,
)

results = matcher.match(
    resume_text=resume_text,
    user_interests=preferences.research_interests,
    user_techniques=preferences.techniques,
    user_preferences=preferences.to_dict(),
)
```

### Fast Matching (Keywords Only)

```python
# Fast matching without LLM (~50ms)
results = matcher.match_fast(resume_text, top_k=50)
```

## API Integration

### Flask Integration

```python
from services.matching.api import register_routes
from flask import Flask

app = Flask(__name__)

# Register matching routes
register_routes(
    app,
    faculty_data_path="faculty_pipeline/output/harvard_university_20260120_162804.json"
)

# Routes available:
# - GET /api/matching/v3/questions
# - POST /api/matching/v3/match
# - POST /api/matching/v3/match/fast
```

### Standalone Flask App

```python
from services.matching.api import create_flask_app

app = create_flask_app(
    faculty_data_path="faculty_pipeline/output/harvard_university_20260120_162804.json"
)

if __name__ == "__main__":
    app.run(debug=True)
```

## Scoring Components

The matching algorithm uses a 100-point scoring system:

1. **Keyword Score (15 points)**: Direct keyword overlap between student and faculty
2. **Semantic Score (25 points)**: Embedding-based semantic similarity
3. **Domain Score (15 points)**: Research domain alignment (life_sciences, computer_science, etc.)
4. **Technique Score (20 points)**: Technical skills and lab techniques match
5. **Experience Score (15 points)**: Academic level appropriateness
6. **Activity Score (10 points)**: Faculty research activity (h-index, publications)

### Quality Thresholds

- **Excellent**: ≥ 75 points
- **Good**: ≥ 60 points
- **Moderate**: ≥ 45 points
- **Weak**: < 45 points

## User Preferences

The service collects user preferences through structured questions:

- Research interests
- Technical skills/techniques
- Experience level (undergraduate/masters/phd/postdoc)
- Lab type preference (wet/dry/mixed/any)
- Location preferences
- Duration preferences
- Funding requirements
- Visa status

See `user_preferences.py` for details.

## Example

See `example_usage.py` for complete examples:

```bash
python services/matching/example_usage.py
```

## File Structure

```
services/matching/
├── __init__.py              # Package exports
├── models.py                # Data models (StudentProfile, FacultyProfile, MatchResult)
├── extractor.py             # Student profile extraction
├── scorer.py                # Multi-stage scoring engine
├── embedding_service.py     # Embedding computation with caching
├── matcher.py               # Main matcher class
├── api.py                   # API wrapper for Flask integration
├── user_preferences.py      # User preferences and questions
├── requirements.txt         # Python dependencies
├── example_usage.py        # Usage examples
└── README.md               # This file
```

## Configuration

### Environment Variables

- `OPENAI_API_KEY`: Required for embeddings and explanations

### Cache Directory

Embeddings are cached in `embeddings_cache/` directory by default. This can be customized when initializing `EmbeddingService`.

## Performance

- **Fast matching**: ~50ms for 600 faculty (keywords only)
- **Full matching**: ~3-5 seconds (with embeddings and explanations)
- **Embedding precomputation**: ~30-60 seconds for 600 faculty (one-time)

## Limitations

- Requires OpenAI API key for full functionality
- Embedding computation requires internet connection
- First run may be slower due to embedding computation

## Integration with RIQ

To integrate into the main RIQ application:

1. Import the matcher:
```python
from services.matching import SophisticatedMatcher
```

2. Or use the API wrapper:
```python
from services.matching.api import register_routes
register_routes(app, faculty_data_path="path/to/faculty.json")
```

3. The service automatically handles faculty data format from the pipeline.

## License

Part of RIQ LabMatch project.
