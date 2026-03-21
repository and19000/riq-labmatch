# Archived templates

## `matches_profile_mvp_202503.html`

Previous **My Matches** page: profile + `MatchingService` (5-question onboarding, paginated table, thinking bar).

Replaced by the tag-based **My Matches** flow (`my_matches.html`) — dropdown questions, top 5 cards, no ML.

To restore the old UI temporarily, copy this file back to `frontend/templates/matches_legacy.html` and add a dedicated Flask route that renders it (not recommended for production).
