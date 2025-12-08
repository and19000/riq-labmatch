# RIQ Lab Matcher - Design Document

## Overview

RIQ Lab Matcher is a Flask-based web application designed to connect students with research opportunities by matching them with Principal Investigators (PIs) at top-tier institutions. The platform leverages OpenAI's GPT-4o-mini model to provide AI-powered lab matching and personalized email drafting capabilities. The application serves as a comprehensive tool for students navigating the research application process, from discovering relevant labs to drafting professional cold emails.

## Design Philosophy & Visual Inspiration

Our design philosophy centers on creating an intuitive, modern interface that feels both professional and approachable. We drew inspiration from a diverse range of high-quality web experiences, including SwiftRead's clean information architecture, Apple's minimalist design language, OpenAI's conversational interfaces, Google DeepMind's scientific aesthetic, Reddit's functional layouts, and NVIDIA's technical sophistication.

The visual design emphasizes a dark mode theme with a blue-purple gradient color scheme, chosen for both aesthetic appeal and practical reasons. Dark mode reduces eye strain during extended use, while the blue-purple gradient evokes themes of space, discovery, and scientific exploration—concepts that align with the research matching mission. The gradient also provides visual continuity throughout the application, creating a cohesive brand identity that extends from the logo to interactive elements.

### Homepage Design

The homepage features a rotating torus animation in the background, inspired by Lila Sciences' spinning torus visualization. This design choice serves multiple purposes: it creates visual interest that draws users in, represents the vastness and interconnectedness of research opportunities (much like a galaxy), and provides a distinctive visual identity that sets RIQ apart from typical academic platforms. The torus animation is implemented using CSS keyframe animations, ensuring smooth performance without requiring heavy JavaScript libraries.

The typography follows Apple's design system, utilizing system fonts (`-apple-system`, `BlinkMacSystemFont`, `system-ui`) for a native feel across different operating systems. This approach ensures consistent rendering and optimal readability while maintaining the modern aesthetic users expect from contemporary web applications.

Below the hero section, we implemented three feature cards that showcase the core functionality: AI-powered matching, email drafting, and lab browsing. These cards use a gradient background system (blue-to-purple) that matches our overall color scheme, with each card having a distinct gradient variant to create visual hierarchy. We replaced emoji icons with custom SVG graphics to maintain a professional appearance while preserving the visual communication of each feature's purpose.

The statistics section provides concrete metrics about the platform's scope, highlighting the number of institutions and labs available. This section uses a blue-to-purple gradient for headings and numbers, reinforcing the brand identity while making key information stand out. The "Browse Labs" call-to-action at the bottom serves as a natural progression point for users who have scrolled through the entire homepage, indicating they're ready to explore available opportunities.

### Logo Design: The Insight Ring

The RIQ logo evolved from an initial magnifying glass concept to an "Insight Ring" design—a clean torus/ring with the letters "RIQ" subtly integrated at the bottom. The logo features three to four small orbiting dots that animate around the ring, creating a sense of movement and discovery. This design metaphorically represents the process of finding insights (the ring) through exploration (the orbiting dots), perfectly aligning with the platform's mission of connecting students with research opportunities.

The logo uses a blue-to-purple gradient with glow effects, creating visual depth and ensuring it stands out against the dark background. The gradient and glow effects are implemented using CSS filters and SVG gradients, allowing for scalable, crisp rendering at any size.

## Technical Architecture

### Backend Framework: Flask

We chose Flask as our web framework for its simplicity, flexibility, and Python-native ecosystem. Flask's lightweight nature allows for rapid development while providing all necessary features for a web application of this scope. The framework's routing system cleanly separates different application features, making the codebase maintainable and easy to extend.

The application follows a traditional Model-View-Controller (MVC) pattern, with database models defined using SQLAlchemy, route handlers in `app.py`, and presentation logic in Jinja2 templates. This separation of concerns makes the codebase easier to understand, test, and modify.

### Database Design: SQLite with SQLAlchemy ORM

We use SQLite as our database engine, which is ideal for a development and small-to-medium scale deployment. SQLite requires no separate server process, simplifies deployment, and provides excellent performance for read-heavy workloads typical of a lab matching platform.

The database schema consists of five main models:

1. **User**: Stores account information including username, email, and password hash. We use Werkzeug's password hashing with `pbkdf2:sha256` (compatible with Python 3.9) to securely store passwords.

2. **SavedPI**: Tracks which PIs each user has saved, with a unique constraint preventing duplicate saves. This many-to-many relationship allows users to build personalized lists of interesting labs.

3. **Resume**: Stores uploaded resume files and extracted text content. The extracted text is crucial for AI-powered matching, as it provides context about the student's background, skills, and experience.

4. **UserProfile**: Contains additional user information such as major field, year in school, research interests, and preferred techniques. This data enhances the matching algorithm's accuracy by providing structured information beyond the resume text.

5. **PasswordResetToken**: Implements secure password reset functionality using time-limited, single-use tokens. Tokens expire after one hour and are marked as used after successful password reset to prevent replay attacks.

The database initialization includes migration logic to handle schema changes gracefully, automatically adding new columns (like `username` and `year_in_school`) to existing tables without requiring manual database modifications.

### AI Integration: OpenAI GPT-4o-mini

The application leverages OpenAI's GPT-4o-mini model for two primary functions: lab matching and email generation. We chose GPT-4o-mini over larger models because it provides excellent performance at a significantly lower cost, making the application economically viable while maintaining high-quality outputs.

#### Lab Matching Algorithm

The matching algorithm processes faculty data in parallel batches to optimize performance. Instead of evaluating labs sequentially (which would take minutes), we split the faculty list into batches of 10 labs each and process up to 100 labs using Python's `ThreadPoolExecutor`. This parallel processing approach reduces matching time from several minutes to under 30 seconds for typical workloads.

The matching prompt instructs the AI to score each lab based on multiple criteria: 40% research area match, 25% skills alignment, 15% academic level appropriateness, 10% department fit, and 10% research impact (H-index). The AI returns a JSON array with PI IDs, scores (0-100), and brief reasoning for each match. We filter out matches below 50 and rank results from highest to lowest score.

The algorithm uses a low temperature setting (0.2) to ensure consistent, reliable scoring across multiple runs. This deterministic approach is crucial for user trust—students should see similar results when re-running matches with the same resume.

#### Email Drafting System

The email drafting feature generates personalized cold emails by combining PI information, student background, and optional research interests. The system prompt emphasizes natural, conversational tone—specifically instructing the AI to avoid corporate jargon, overly formal language, or robotic phrasing. This is critical because academic emails should sound authentic and genuine, not like business correspondence.

The prompt includes detailed guidelines about email structure (subject line, greeting, body paragraphs, closing) and tone (warm but professional, specific but not gushing, confident but humble). We use a slightly higher temperature (0.8) for email generation to allow for natural variation while maintaining quality.

For bulk email generation, the system processes multiple PIs sequentially, generating personalized emails for each selected PI. Each email is tailored to the specific PI's research areas, techniques, and background, ensuring that bulk generation doesn't sacrifice personalization.

### Frontend Implementation

#### CSS Architecture: Design System with CSS Variables

The stylesheet uses CSS custom properties (variables) to create a consistent design system. This approach centralizes color definitions, spacing, typography, and animation timing, making it easy to maintain visual consistency and implement theme changes. The variable system includes:

- Background colors at different elevation levels (`--bg`, `--bg-elevated`, `--bg-card`)
- Accent colors with variants (`--accent`, `--accent-soft`, `--accent-hover`)
- Text colors for different emphasis levels (`--text-main`, `--text-muted`, `--text-dim`)
- Border radius and shadow definitions for consistent styling
- Transition timing for smooth animations

#### Responsive Design and Animations

The application uses CSS Grid and Flexbox for responsive layouts that adapt to different screen sizes. Key animations include:

- **Torus Rotation**: Implemented using CSS `@keyframes` with `transform: rotateY()` to create a 3D rotation effect. The animation runs continuously on the homepage.

- **Gradient Wave Background**: Non-homepage pages feature an animated blue-purple gradient that moves in a wave-like motion. This is achieved using multiple layered gradients with `@keyframes` animations that shift gradient positions, creating a flowing, organic movement pattern.

- **Black Hole Graphic**: The email drafting page includes an animated black hole visualization with accretion rings and twinkling stars. This uses CSS animations to create rotating rings and pulsing effects, reinforcing the space/galaxy theme.

- **Loading Indicators**: AI processing operations show animated thinking dots and progress bars to provide user feedback during potentially long-running operations.

#### JavaScript and AJAX Integration

We use vanilla JavaScript (no frameworks) to keep the application lightweight. Key JavaScript functionality includes:

- **AJAX Form Submissions**: Save buttons use AJAX to submit requests without page reloads, maintaining scroll position and providing instant visual feedback. This significantly improves user experience, especially on pages with long lists of PIs.

- **Dynamic UI Updates**: When a PI is saved, the button immediately updates to show "✓ Saved" and a badge appears next to the PI's name. This instant feedback creates a responsive, modern feel.

- **Email Quality Checks**: Client-side validation checks email length, personalization, and tone before displaying the generated email, providing immediate feedback to users.

### Security Considerations

#### Password Security

Passwords are never stored in plain text. We use Werkzeug's `generate_password_hash()` with `pbkdf2:sha256` and a 16-byte salt. This hashing method is computationally expensive, making brute-force attacks impractical even if the database is compromised.

#### Session Management

Flask sessions use a secret key to cryptographically sign session cookies, preventing tampering. The session stores only the user ID, minimizing the risk if session data is intercepted.

#### File Upload Security

Uploaded files are validated for allowed extensions (PDF and DOCX only) and sanitized using `secure_filename()` to prevent path traversal attacks. Files are stored with user-specific prefixes to prevent conflicts and unauthorized access.

#### Password Reset Security

Password reset tokens are generated using `secrets.token_urlsafe()`, which creates cryptographically secure random tokens. Tokens expire after one hour and are single-use, preventing replay attacks. The token generation and verification functions include comprehensive error handling to prevent timing attacks.

### Performance Optimizations

#### Parallel Batch Processing

The most significant performance optimization is the parallel batch processing for lab matching. By processing multiple batches simultaneously using `ThreadPoolExecutor`, we achieve approximately 10x speedup compared to sequential processing. This makes the matching feature practical for real-world use, as users would abandon the page if matching took several minutes.

#### Database Query Optimization

We minimize database queries by:
- Using `filter_by()` with indexed columns (user_id, pi_id)
- Fetching related data in single queries where possible
- Using sets for membership testing (O(1) lookup) instead of lists (O(n))

#### Static Asset Caching

Static assets (CSS, JavaScript, images) are served with appropriate cache headers, allowing browsers to cache these files and reduce server load for repeat visitors.

#### Template Caching

Jinja2 templates are compiled and cached, reducing template rendering overhead on subsequent requests.

## Page-by-Page Design Decisions

### Browse Labs (General Page)

The general browsing page implements a filter system inspired by Harvard's Faculty Program in Neuroscience, providing familiar interaction patterns for users already familiar with academic lab search tools. Filters include institution, field, techniques, and location, allowing users to quickly narrow down results to their preferences.

The page displays PIs in a table format with columns for logo, professor name, information, email, H-index, and actions. The H-index serves as a quick indicator of research impact, helping users identify well-established researchers. The search bar enables quick text-based filtering, complementing the structured filter system.

We implemented AJAX for the save functionality to prevent page reloads and maintain scroll position—a critical UX improvement for pages with long lists of results.

### My Matches Page

The matches page is the core feature of the application, displaying AI-ranked lab matches based on the user's uploaded resume. The page shows match scores (0-100) and brief reasoning for each match, helping users understand why specific labs were recommended.

The page includes a loading overlay that displays while AI processing occurs, providing clear feedback during the potentially long-running matching operation. Once matches are displayed, users can save interesting labs, draft emails directly, or compare multiple labs side-by-side.

The matching algorithm processes up to 100 labs in parallel batches, balancing comprehensiveness with performance. We limit to 100 labs to keep response times reasonable while still providing a substantial number of matches.

### Saved PIs Page

The saved PIs page aggregates all labs a user has expressed interest in. It provides expanded information compared to the matches page, including full research descriptions and lab techniques. Users can compare selected labs, export results as PDF, and remove PIs from their saved list.

The comparison feature allows users to evaluate multiple labs side-by-side, helping them make informed decisions about which opportunities to pursue. The PDF export functionality enables offline review and sharing with advisors or mentors.

### Email Drafting Pages

The single email drafting page features a two-column layout: form inputs on the left and an animated black hole graphic on the right. This layout balances functionality with visual interest, making the email generation process engaging rather than purely utilitarian.

The form only shows saved PIs in the dropdown, ensuring users draft emails for labs they've already expressed interest in. This design choice prevents users from drafting emails to labs they haven't properly evaluated, improving email quality and reducing spam.

The bulk email page uses a checkbox interface for selecting multiple PIs, with the same visual design as the single email page for consistency. Generated emails are displayed in cards that match the single email page styling, creating a cohesive experience across both workflows.

### Help Page

The help page serves as both documentation and a feedback mechanism. It includes step-by-step guides for using each feature, frequently asked questions compiled from test users and actual PIs/grad students, and tips for getting into research. The feedback form at the bottom allows users to report issues or suggest improvements.

In retrospect, we could enhance the help page with direct email contact functionality, but the current feedback form provides a sufficient mechanism for user communication during the development phase.

### Account/Profile Page

The account page displays user profile information and includes a progress bar visualization showing profile completion. This gamification element encourages users to provide complete information, which improves matching accuracy. The page allows users to update their profile information, including major field, year in school, research interests, and preferred techniques.

## Additional Technical Considerations

### Error Handling and User Feedback

The application includes comprehensive error handling at multiple levels:
- Form validation provides immediate feedback for user input errors
- Database operations are wrapped in try-except blocks to handle constraint violations gracefully
- OpenAI API calls include error handling for rate limits, network issues, and API errors
- User-facing error messages are clear and actionable, avoiding technical jargon

### Scalability Considerations

While the current implementation uses SQLite and processes a limited number of labs, the architecture supports future scaling:

- The database models can be migrated to PostgreSQL or MySQL with minimal code changes (SQLAlchemy abstracts database differences)
- The parallel batch processing can be extended to process more labs or moved to a background job queue (e.g., Celery) for even better performance
- Static assets can be served from a CDN to reduce server load
- The application can be containerized using Docker for consistent deployment across environments

### Code Maintainability

We've added comprehensive, human-readable comments throughout the codebase explaining the purpose and function of each section. These comments use natural language rather than technical jargon, making the codebase accessible to developers with varying experience levels. The comments explain not just what the code does, but why design decisions were made, which is crucial for future maintenance and feature development.

## Future Improvements and Considerations

Several areas could be enhanced in future iterations:

1. **Resume Parsing**: Currently, resume text extraction is a placeholder. Implementing proper PDF and DOCX parsing using libraries like PyPDF2 or python-docx would improve matching accuracy by extracting structured information (education, experience, skills) rather than relying on raw text.

2. **Email Sending**: The application generates email drafts but doesn't send them. Integrating with an email service (SendGrid, AWS SES, or SMTP) would complete the workflow, allowing users to send emails directly from the platform.

3. **Advanced Matching**: The current matching algorithm could be enhanced with machine learning models trained on successful student-PI matches, providing more nuanced scoring beyond the current rule-based approach.

4. **Analytics**: Adding usage analytics would help understand how users interact with the platform, identifying pain points and opportunities for improvement.

5. **Mobile Optimization**: While the application is responsive, a dedicated mobile app or Progressive Web App (PWA) could provide a more native mobile experience.

6. **Social Features**: Adding the ability to share matches with advisors, compare notes with peers, or see which labs are popular could enhance the platform's value.

7. **PI Verification**: Allowing PIs to claim and verify their profiles would ensure data accuracy and enable two-way communication.

8. **Integration with University Systems**: Integrating with university authentication systems (Shibboleth, CAS) would simplify account creation and provide access to verified student information.

## Conclusion

RIQ Lab Matcher represents a comprehensive solution to the challenge of connecting students with research opportunities. The design balances aesthetic appeal with functional clarity, leveraging modern web technologies and AI capabilities to create a tool that genuinely helps students navigate the research application process. The technical architecture prioritizes maintainability, performance, and user experience, creating a solid foundation for future enhancements and scaling.

The combination of thoughtful design, robust backend implementation, and AI-powered features creates a platform that addresses a real need in the academic community. By drawing inspiration from successful web applications while maintaining a unique visual identity, RIQ Lab Matcher stands out as both functional and memorable.

