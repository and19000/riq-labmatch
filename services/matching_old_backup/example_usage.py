#!/usr/bin/env python3
"""
Example usage of the V3 Sophisticated Matching Algorithm.

This script demonstrates how to use the matching service.
"""

import json
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from services.matching import SophisticatedMatcher
from services.matching.user_preferences import UserPreferences, collect_user_preferences_interactive


def example_basic_matching():
    """Basic example of matching."""
    print("=" * 60)
    print("Example 1: Basic Matching")
    print("=" * 60)
    
    # Path to faculty data
    faculty_data_path = "faculty_pipeline/output/harvard_university_20260120_162804.json"
    
    if not os.path.exists(faculty_data_path):
        print(f"Error: Faculty data file not found: {faculty_data_path}")
        print("Please update the path to your faculty data file.")
        return
    
    # Sample resume text
    resume_text = """
    John Doe
    Computer Science Major, Junior Year
    
    Research Experience:
    - Worked on machine learning projects using Python and TensorFlow
    - Developed neural network models for image classification
    - Published paper on deep learning applications
    
    Skills:
    - Python, TensorFlow, PyTorch
    - Machine Learning, Deep Learning
    - Data Analysis, Statistical Modeling
    
    Interests:
    - Artificial Intelligence
    - Computer Vision
    - Natural Language Processing
    """
    
    # Initialize matcher
    print("Initializing matcher...")
    matcher = SophisticatedMatcher(
        faculty_data_path=faculty_data_path,
        precompute_embeddings=True,
    )
    
    # Match
    print("Running matching algorithm...")
    results = matcher.match(
        resume_text=resume_text,
        user_interests=["machine learning", "AI", "computer vision"],
        user_techniques=["Python", "TensorFlow", "deep learning"],
        top_k=10,
        include_explanations=True,
    )
    
    # Display results
    print(f"\nFound {len(results['matches'])} matches")
    print(f"Total faculty: {results['total_faculty']}")
    print(f"Duration: {results['metadata']['duration_ms']}ms")
    print("\nTop 5 Matches:")
    print("-" * 60)
    
    for i, match in enumerate(results['matches'][:5], 1):
        print(f"\n{i}. {match['name']}")
        print(f"   Score: {match['total_score']:.1f}/100 ({match['quality']})")
        print(f"   H-index: {match['h_index']}")
        print(f"   Institution: {match['institution']}")
        if match.get('personalized_reason'):
            print(f"   Reason: {match['personalized_reason'][:100]}...")
        if match.get('match_reasons'):
            print(f"   Matched: {', '.join(match['match_reasons'][:2])}")


def example_with_preferences():
    """Example with user preferences."""
    print("\n" + "=" * 60)
    print("Example 2: Matching with User Preferences")
    print("=" * 60)
    
    faculty_data_path = "faculty_pipeline/output/harvard_university_20260120_162804.json"
    
    if not os.path.exists(faculty_data_path):
        print(f"Error: Faculty data file not found: {faculty_data_path}")
        return
    
    resume_text = """
    Jane Smith
    Biology Major, Senior Year
    
    Research Experience:
    - Worked in molecular biology lab
    - Experience with PCR, gel electrophoresis, cell culture
    - Interested in genetics and genomics
    
    Skills:
    - PCR, Western Blot, Cell Culture
    - Microscopy, DNA sequencing
    - Python for data analysis
    """
    
    # Create user preferences
    preferences = UserPreferences(
        research_interests=["genetics", "genomics", "molecular biology"],
        techniques=["PCR", "cell culture", "microscopy"],
        experience_level="undergraduate",
        lab_type_preference="wet",
        preferred_duration="summer",
        funding_required=True,
    )
    
    # Initialize matcher
    matcher = SophisticatedMatcher(
        faculty_data_path=faculty_data_path,
        precompute_embeddings=True,
    )
    
    # Match with preferences
    results = matcher.match(
        resume_text=resume_text,
        user_interests=preferences.research_interests,
        user_techniques=preferences.techniques,
        user_preferences=preferences.to_dict(),
        top_k=10,
    )
    
    print(f"\nFound {len(results['matches'])} matches")
    print("\nTop 3 Matches:")
    for i, match in enumerate(results['matches'][:3], 1):
        print(f"\n{i}. {match['name']} - Score: {match['total_score']:.1f}")


def example_fast_matching():
    """Example of fast keyword-only matching."""
    print("\n" + "=" * 60)
    print("Example 3: Fast Matching (Keywords Only)")
    print("=" * 60)
    
    faculty_data_path = "faculty_pipeline/output/harvard_university_20260120_162804.json"
    
    if not os.path.exists(faculty_data_path):
        print(f"Error: Faculty data file not found: {faculty_data_path}")
        return
    
    resume_text = "Machine learning, deep learning, neural networks, Python, data science"
    
    matcher = SophisticatedMatcher(
        faculty_data_path=faculty_data_path,
        precompute_embeddings=False,  # Not needed for fast matching
    )
    
    import time
    start = time.time()
    results = matcher.match_fast(resume_text, top_k=20)
    elapsed = time.time() - start
    
    print(f"Fast matching completed in {elapsed*1000:.1f}ms")
    print(f"Found {len(results)} matches")
    print("\nTop 5:")
    for i, match in enumerate(results[:5], 1):
        print(f"{i}. {match['name']} - Score: {match['score']:.1f}")


def example_api_usage():
    """Example of using the API wrapper."""
    print("\n" + "=" * 60)
    print("Example 4: API Usage")
    print("=" * 60)
    
    from services.matching.api import MatchingAPI
    
    faculty_data_path = "faculty_pipeline/output/harvard_university_20260120_162804.json"
    
    if not os.path.exists(faculty_data_path):
        print(f"Error: Faculty data file not found: {faculty_data_path}")
        return
    
    # Initialize API
    api = MatchingAPI(faculty_data_path=faculty_data_path)
    
    # Get questions
    questions = api.get_questions()
    print(f"\nAvailable questions: {len(questions)}")
    for q in questions[:3]:
        print(f"  - {q['question']}")
    
    # Match
    resume_text = "Computer science student interested in AI and machine learning"
    results = api.match(
        resume_text=resume_text,
        user_interests=["AI", "machine learning"],
        top_k=5,
    )
    
    print(f"\nMatches: {len(results['matches'])}")


if __name__ == "__main__":
    print("RIQ LabMatch - V3 Matching Algorithm Examples")
    print("=" * 60)
    
    # Check for OpenAI API key
    if not os.environ.get("OPENAI_API_KEY"):
        print("\n⚠️  Warning: OPENAI_API_KEY not set")
        print("   Some features (embeddings, explanations) will be disabled")
        print("   Set it with: export OPENAI_API_KEY='your-key'")
        print()
    
    try:
        example_basic_matching()
        example_with_preferences()
        example_fast_matching()
        example_api_usage()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
    except Exception as e:
        print(f"\n\nError: {e}")
        import traceback
        traceback.print_exc()
