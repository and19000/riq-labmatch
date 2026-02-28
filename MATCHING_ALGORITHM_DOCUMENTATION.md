# RIQ LabMatch - Matching Algorithm Documentation

**Last Updated:** January 20, 2026  
**Project:** RIQ LabMatch  
**Status:** Current Implementation - V1 & V2 Algorithms

---

## Executive Summary

RIQ LabMatch uses **three matching algorithm versions** to match user resumes to professors:

1. **V1 Algorithm (Original)**: AI-powered matching using OpenAI GPT-4o-mini with parallel batch processing
2. **V2 Algorithm (Current Default)**: Deterministic scoring system with LLM-based extraction
3. **V3 Algorithm (Sophisticated)**: Multi-stage filtering with semantic understanding and enhanced user preferences

V2 is the default system, with V1 as a fallback. V3 is the newest sophisticated algorithm with multi-stage filtering.

---

## V1 Matching Algorithm (Original System)

### Overview
The V1 algorithm uses OpenAI's GPT-4o-mini model to directly score matches between student resumes and faculty profiles. It processes faculty in parallel batches for performance.

### Implementation Location
- **File:** `/Users/kerrynguyen/Documents/riq-labmatch/app.py`
- **Function:** `process_faculty_batch()` (lines 679-753)
- **Route:** `/matches` endpoint (lines 1000-1156)

### Algorithm Details

#### Scoring Criteria (as specified in prompt):
- **40%** - Research area match
- **25%** - Skills alignment
- **15%** - Academic level appropriateness
- **10%** - Department fit
- **10%** - Research impact (H-index)

#### Score Ranges:
- **90-100**: Exceptional match
- **80-89**: Excellent match
- **70-79**: Good match
- **60-69**: Moderate match
- **50-59**: Weak match
- **<50**: Excluded from results

#### Processing Method:
1. **Batch Processing**: Faculty split into batches of 10 labs each
2. **Parallel Execution**: Up to 20 workers using `ThreadPoolExecutor`
3. **Batch Limit**: Processes top 100 labs (configurable)
4. **Temperature**: 0.2 (low for consistency)
5. **Model**: GPT-4o-mini
6. **Max Tokens**: 2000 per batch response

#### Prompt Structure:
```
Match student resume with compatible labs. Return JSON array only.

STUDENT: [resume text - first 500 chars]

LABS (Batch X/Y):
[Concise faculty summaries: name, ID, research areas, techniques, department]

Scoring (40% research match, 25% skills, 15% level, 10% dept, 10% impact):
- 90-100: Exceptional | 80-89: Excellent | 70-79: Good | 60-69: Moderate | 50-59: Weak | <50: Exclude

Return JSON array: [{"pi_id": "id", "score": 85, "reason": "brief reason"}]
Only include labs with score >= 50. Rank highest to lowest.
```

#### Output Format:
```json
[
  {
    "pi_id": "faculty_id",
    "score": 85,
    "reason": "Strong research area match in computational neuroscience"
  }
]
```

#### Performance:
- **Speed**: ~30 seconds for 100 labs (vs. several minutes sequential)
- **Parallelism**: 20 concurrent workers
- **Fallback**: Shows all labs with score 50 if AI fails

---

## V2 Matching Algorithm (Current Default)

### Overview
The V2 algorithm uses a **deterministic scoring system** where LLMs are only used for data extraction, not scoring. This ensures consistent, explainable results.

### Implementation Location
- **Main Entry:** `/Users/kerrynguyen/Documents/riq-labmatch/services/matching/match.py`
- **Scoring Engine:** `/Users/kerrynguyen/Documents/riq-labmatch/services/matching/scorer.py`
- **Route:** `/matches` endpoint with `matching_version=v2` (default)

### Algorithm Details

#### Scoring Breakdown (Total: 105 points):

1. **Research Interest Match (40 points)**
   - **Exact phrase match**: 14 points (35% of 40)
   - **Keyword overlap**: 12 points (30% of 40)
   - **Embedding similarity**: 10 points (25% of 40) - uses OpenAI text-embedding-3-small
   - **Domain alignment**: 4 points (10% of 40)

2. **Techniques & Skills Match (25 points)**
   - Matches student techniques to faculty lab techniques
   - Recency weighting (recent experience weighted higher)
   - User-specified techniques weighted 1.5x vs resume techniques
   - Confidence penalties for low-confidence matches

3. **Experience Level Fit (15 points)**
   - Undergraduate/Masters/PhD/Postdoc compatibility
   - Penalties for mismatches (e.g., undergrad in advanced lab)
   - Funding considerations for PhD/postdoc students

4. **Practical Fit & Constraints (10 points)**
   - Location match: 4 points
   - Lab type (wet/dry/both): 2 points
   - Timing: 2 points
   - Funding availability: 1.5 points
   - Visa considerations: 0.5 points

5. **Department/Institution Context (5 points)**
   - Neutral scoring (doesn't penalize based on prestige)

6. **Activity/Impact Signals (5 points)**
   - Recent publication count
   - Research activity level

7. **Response Rate Bonus (5 points)**
   - Teaches courses: +2 points
   - Has recruiting page: +1.5 points
   - Accepts interns: +2 points
   - Current trainees > 5: +1.5 points

#### Match Quality Thresholds:
- **Excellent**: ≥ 85 points
- **Good**: ≥ 70 points
- **Moderate**: ≥ 55 points
- **Weak**: < 55 points

#### Processing Pipeline:
1. **Filter invalid professors** (early optimization)
2. **Extract student profile** (with caching)
   - Research interests
   - Techniques (with recency)
   - Experience level
   - Constraints
3. **Extract faculty profiles** (with caching)
   - Research areas, keywords, domains
   - Techniques
   - Level signals
   - Activity signals
4. **Score all matches** (deterministic Python code)
5. **Sort by score**
6. **Generate explanations** (only for top K*3 candidates)
7. **Return top K matches**

#### Key Features:
- **Deterministic**: Same inputs always produce same outputs
- **Explainable**: Detailed breakdown of scores and reasons
- **Cached**: Student and faculty profiles cached for performance
- **Optimized**: Early filtering, minimal LLM calls (only for extraction)

#### Output Format:
```python
MatchResult(
    match_id: str,
    timestamp: datetime,
    top_matches: List[MatchExplanation],
    all_scored: List[Dict],
    metadata: Dict
)

MatchExplanation(
    pi_id: str,
    name: str,
    institution: str,
    total_score: float,  # 0-105
    breakdown: ScoreBreakdown,  # Detailed component scores
    reasons: List[str],  # Human-readable explanations
    evidence: MatchEvidence,  # Matched keywords, techniques, etc.
    match_quality: str,  # "excellent", "good", "moderate", "weak"
    concerns: List[str],  # Potential issues
    confidence: float  # 0.0-1.0
)
```

---

## Available Data for Matching

### Faculty Research Profiles

Each professor in the system has a `ResearchProfile` containing:

#### 1. **Topics** (Primary Research Areas)
- **Source:** OpenAlex API
- **Format:** List of topic objects with `name` and `score` (0.0-1.0)
- **Count:** Up to 15 topics per professor
- **Example:**
  ```json
  {
    "name": "Molecular Junctions and Nanostructures",
    "score": 1.0
  }
  ```

#### 2. **Concepts** (Research Concepts)
- **Source:** OpenAlex API
- **Format:** List of concept objects with `name`, `level`, and `score`
- **Levels:** 0 (field-level) to higher (specific concepts)
- **Count:** Up to 10 concepts per professor
- **Example:**
  ```json
  {
    "name": "Etching (microfabrication)",
    "level": 0,
    "score": 0.694
  }
  ```

#### 3. **Fields** (Research Fields)
- **Source:** Derived from concepts where `level == 0`
- **Format:** List of field name strings
- **Count:** Up to 5 fields per professor
- **Example:** `["Chemistry", "Materials Science", "Nanotechnology"]`

#### 4. **Keywords** (Research Keywords)
- **Source:** Derived from topics (preferred) or concepts
- **Format:** List of keyword strings
- **Count:** Up to 15 keywords per professor
- **Example:** `["Microfluidics", "Nanofabrication", "Molecular Junctions"]`

#### 5. **Research Summary**
- **Format:** Semicolon-separated string of top 5 topics/concepts
- **Purpose:** Human-readable summary for display

### Additional Faculty Metadata

- **h_index:** Citation impact metric
- **works_count:** Number of publications
- **cited_by_count:** Total citations
- **institution:** University affiliation
- **email:** Contact information (when available)
- **website:** Personal/lab website URL

---

## Implied Matching Algorithm (Based on Data Structure)

While no explicit matching code was found, the data structure suggests a matching algorithm would likely use:

### Matching Components

1. **Topic Matching**
   - Compare user resume keywords/skills to professor topics
   - Weight by topic `score` (higher score = more relevant)
   - Top 5-10 topics likely most important

2. **Concept Matching**
   - Match user research interests to professor concepts
   - Consider concept `level` (field-level vs specific)
   - Weight by concept `score`

3. **Keyword Matching**
   - Direct keyword overlap between resume and professor keywords
   - Simple text matching or semantic similarity
   - Count overlapping keywords

4. **Field Matching**
   - Match user's field of study to professor's research fields
   - Broad category matching (e.g., "Chemistry" matches "Chemistry")

### Potential Scoring Approach

A matching score could be calculated as:

```
Match Score = 
  (Topic Overlap Score × 0.4) +
  (Concept Overlap Score × 0.3) +
  (Keyword Overlap Score × 0.2) +
  (Field Overlap Score × 0.1)
```

Where each component score is normalized (0.0-1.0).

---

## Current Implementation Status

### ✅ Fully Implemented
- **V1 Matching Algorithm**: AI-powered batch processing with GPT-4o-mini
- **V2 Matching Algorithm**: Deterministic scoring system (default)
- Faculty data extraction pipeline (v4.4)
- Research profile extraction from OpenAlex
- Resume text extraction (PDF/DOCX)
- User profile system (major, year, research interests, techniques)
- Matching API endpoint (`/matches`)
- User interface for viewing matches
- Parallel batch processing for performance
- Caching system for student/faculty profiles

### 📊 Data Sources
- **Faculty Data**: 600+ Harvard professors with research profiles
- **Student Data**: Uploaded resumes + user profile information
- **OpenAI**: GPT-4o-mini for V1 matching, embeddings for V2 similarity

---

## Code & Data Locations

### Matching Algorithm Code
- **V1 Algorithm:** `/Users/kerrynguyen/Documents/riq-labmatch/app.py`
  - `process_faculty_batch()`: Lines 679-753
  - `/matches` route: Lines 1000-1156
- **V2 Algorithm:** `/Users/kerrynguyen/Documents/riq-labmatch/services/matching/`
  - `match.py`: Main entry point
  - `scorer.py`: Deterministic scoring engine
  - `student_extractor.py`: Extract student profile from resume
  - `faculty_extractor.py`: Extract faculty profile from data
  - `explainer.py`: Generate match explanations
  - `config.py`: Scoring configuration
- **V3 Algorithm:** `/Users/kerrynguyen/Projects/riq-labmatch/services/matching/`
  - `matcher.py`: Main sophisticated matcher
  - `scorer.py`: Multi-stage scoring engine
  - `extractor.py`: LLM-powered student profile extraction
  - `embedding_service.py`: Embedding computation with caching
  - `models.py`: Data models (StudentProfile, FacultyProfile, MatchResult)
  - `api.py`: API wrapper for Flask integration
  - `user_preferences.py`: User preferences and questions collection

### Faculty Data Files
- **JSON:** `faculty_pipeline/output/harvard_university_20260120_162804.json`
- **CSV:** `faculty_pipeline/output/harvard_university_20260120_162804.csv`
- **Latest:** Contains 600 Harvard faculty with research profiles

### Faculty Pipeline Code
- **Main Pipeline:** `faculty_pipeline/faculty_pipeline_v4_4.py`
- **Research Profile Class:** Lines 158-190
- **OpenAlex Client:** Lines 1327-1372 (parses research profiles)

---

## V3 Matching Algorithm (Sophisticated - Newest)

### Overview
The V3 algorithm uses **multi-stage filtering** with semantic understanding, combining fast keyword filtering, embedding-based similarity, and detailed scoring with LLM-powered explanations.

### Implementation Location
- **Main Directory:** `/Users/kerrynguyen/Projects/riq-labmatch/services/matching/`
- **Main Matcher:** `matcher.py`
- **Scoring Engine:** `scorer.py`
- **Student Extractor:** `extractor.py`
- **Embedding Service:** `embedding_service.py`
- **API Wrapper:** `api.py`
- **User Preferences:** `user_preferences.py`

### Algorithm Details

#### Architecture:
```
Stage 1: Fast keyword filter (100ms) → Top 100 candidates
Stage 2: Embedding similarity (500ms) → Top 30 candidates  
Stage 3: LLM reasoning (2-3s) → Top 20 with explanations
```

#### Scoring Breakdown (Total: 100 points):

1. **Keyword Score (15 points)**
   - Direct keyword overlap between student and faculty
   - Fast computation, no LLM required

2. **Semantic Score (25 points)**
   - Embedding-based semantic similarity
   - Uses OpenAI text-embedding-3-small
   - Captures conceptual matches beyond keywords

3. **Domain Score (15 points)**
   - Research domain alignment
   - Uses hierarchical taxonomy (life_sciences, computer_science, etc.)

4. **Technique Score (20 points)**
   - Technical skills and lab techniques match
   - Considers both resume and user-provided techniques

5. **Experience Score (15 points)**
   - Academic level appropriateness
   - Considers h-index for mentor availability

6. **Activity Score (10 points)**
   - Faculty research activity
   - Based on h-index and publication count

#### Match Quality Thresholds:
- **Excellent**: ≥ 75 points
- **Good**: ≥ 60 points
- **Moderate**: ≥ 45 points
- **Weak**: < 45 points

#### Key Features:
- **Multi-stage filtering**: Efficiently narrows from 600+ to top matches
- **Semantic understanding**: Uses embeddings for conceptual matching
- **User preferences**: Collects and uses detailed student preferences
- **Personalized explanations**: LLM-generated match reasons and approach suggestions
- **Fast mode**: Keyword-only matching (~50ms) for quick previews
- **Caching**: Embeddings cached for performance

#### Performance:
- **Full matching**: ~3-5 seconds total
- **Fast matching**: ~50ms (keywords only)
- **Cost**: ~$0.01-0.02 per match request
- **Embedding precomputation**: ~30-60 seconds for 600 faculty (one-time)

#### User Preferences:
V3 collects enhanced user preferences:
- Research interests
- Technical skills/techniques
- Experience level
- Lab type preference (wet/dry/mixed/any)
- Location preferences
- Duration preferences
- Funding requirements
- Visa status

#### Output Format:
```python
{
    "matches": [
        {
            "pi_id": "faculty_id",
            "name": "Professor Name",
            "institution": "Harvard University",
            "total_score": 82.5,
            "quality": "excellent",
            "confidence": 0.85,
            "breakdown": {
                "keyword": 12.0,
                "semantic": 20.5,
                "domain": 15.0,
                "technique": 18.0,
                "experience": 12.0,
                "activity": 5.0
            },
            "match_reasons": ["Domain match: computer_science", "Skills match: Python, TensorFlow"],
            "concerns": [],
            "matched_topics": ["machine learning", "neural networks"],
            "matched_techniques": ["Python", "TensorFlow"],
            "personalized_reason": "Strong match in machine learning...",
            "suggested_approach": "Mention your experience with neural networks..."
        }
    ],
    "student_profile": {...},
    "metadata": {...}
}
```

#### Usage:
```python
from services.matching import SophisticatedMatcher

matcher = SophisticatedMatcher(
    faculty_data_path="faculty_pipeline/output/harvard_university_20260120_162804.json"
)

results = matcher.match(
    resume_text=resume_text,
    user_interests=["machine learning", "AI"],
    user_techniques=["Python", "TensorFlow"],
    top_k=20
)
```

---

## Algorithm Comparison

| Feature | V1 Algorithm | V2 Algorithm | V3 Algorithm |
|---------|-------------|--------------|--------------|
| **Scoring Method** | AI-powered (GPT-4o-mini) | Deterministic Python | Multi-stage + Embeddings |
| **Consistency** | Variable (temperature 0.2) | Fully deterministic | Deterministic + LLM explanations |
| **Explainability** | Brief reasons | Detailed breakdown | Personalized explanations |
| **Performance** | ~30s for 100 labs | Optimized with caching | ~3-5s with multi-stage |
| **Cost** | Higher (per-match API calls) | Lower (embeddings + extraction) | Low (~$0.01-0.02/match) |
| **Default** | Fallback | ✅ Current default | ✅ Newest sophisticated |
| **Score Range** | 0-100 | 0-105 | 0-100 |
| **Components** | 5 weighted factors | 7 detailed components | 6 components + multi-stage |
| **User Preferences** | Basic | Enhanced | ✅ Comprehensive |
| **Fast Mode** | No | No | ✅ Yes (~50ms) |

## Usage

### V2 Algorithm (Default)
```python
# Automatically used when accessing /matches
# Can be explicitly requested:
GET /matches?matching_version=v2
```

### V1 Algorithm (Fallback)
```python
# Used if V2 fails or explicitly requested:
GET /matches?matching_version=v1
```

### V3 Algorithm (Sophisticated)
```python
# Using the matching service directly:
from services.matching import SophisticatedMatcher

matcher = SophisticatedMatcher(faculty_data_path="path/to/faculty.json")
results = matcher.match(resume_text, user_interests=["ML"], top_k=20)

# Or via API wrapper:
from services.matching.api import register_routes
register_routes(app, faculty_data_path="path/to/faculty.json")
# Then use: POST /api/matching/v3/match
```

---

## Example Data Structure

```json
{
  "name": "George M. Whitesides",
  "h_index": 233,
  "research": {
    "topics": [
      {"name": "Molecular Junctions and Nanostructures", "score": 1.0},
      {"name": "Nanofabrication and Lithography Techniques", "score": 1.0}
    ],
    "concepts": [
      {"name": "Etching (microfabrication)", "level": 0, "score": 0.694}
    ],
    "fields": [],
    "keywords": [
      "Molecular Junctions and Nanostructures",
      "Nanofabrication and Lithography Techniques"
    ]
  }
}
```

---

## Key Implementation Details

### V1 Algorithm Characteristics
- Uses OpenAI GPT-4o-mini for direct scoring
- Parallel batch processing (20 workers, batches of 10)
- Low temperature (0.2) for consistency
- Filters matches below score 50
- Processes top 100 labs by default

### V2 Algorithm Characteristics
- Deterministic scoring (same inputs = same outputs)
- LLMs only used for extraction, not scoring
- Uses OpenAI embeddings for semantic similarity
- Detailed score breakdown (7 components)
- Caching for performance
- Early filtering of invalid professors
- Generates explanations only for top candidates

### Design Philosophy (from DESIGN.md)
- **Cost-effective**: Uses GPT-4o-mini (cheapest capable model)
- **Fast**: Parallel processing reduces time from minutes to ~30 seconds
- **Reliable**: V2 ensures consistent results
- **Explainable**: Both versions provide reasoning for matches

---

**Document Generated:** January 20, 2026  
**Codebase Version:** v4.4.0 (Faculty Pipeline), V2 Matching (Default)  
**Faculty Data:** 600 Harvard professors extracted  
**Matching Algorithms:** V1 (AI-powered) & V2 (Deterministic) - Both Implemented
