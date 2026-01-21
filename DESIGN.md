# RIQ Lab Matcher - Design Document




Overview




RIQ Lab Matcher is based on Flask and is an application designed to connect students with research opportunities by matching them with Principal Investigators (PIs) at top-tier institutions. We used OpenAI's GPT-4o-mini model to provide AI-powered lab matching and personalized email drafting capabilities. The application serves as a tool for students navigating the research application process, from discovering relevant labs to drafting professional cold emails with the main purpose of bolstering the amount of people invested into research as well as foster interest for those uninterested in research.




Design Philosophy & Visual Inspiration




Our design philosophy centers on creating an intuitive interface that feels both professional and approachable. We drew inspiration from a diverse range of high-quality web experiences, including SwiftRead's information architecture, Apple's minimalist fonts and navigation bar design, OpenAI's conversational interfaces, Google DeepMind's scientific aesthetic as well as inspiration for the cards contained in our homepage, Reddit's functional layouts, and NVIDIA for the dark mode interface.




The visual design emphasizes a dark mode theme with a blue-purple gradient color scheme, chosen for both aesthetic appeal and practical reasons. Dark mode reduces eye strain during extended use, while the blue-purple gradient evokes themes of space, discovery, and scientific exploration—concepts that align with the research matching mission as well as is a nod to the northern lights where we hope research will allow users to find the northern star in their lives. The gradient also provides visual continuity throughout the application, creating a cohesive brand identity that extends from the logo to interactive elements and leaves the users feeling satisfied and inspired once they visit our website.




Desing Home Page




The homepage features a rotating torus animation in the background, inspired by Lila Sciences' spinning torus visualization. This design choice serves multiple purposes: it creates visual interest that draws users in, represents the vastness and interconnectedness of research opportunities (much like a galaxy), and provides a distinctive visual identity that sets RIQ apart from typical academic platforms. The torus animation is implemented using CSS keyframe animations, ensuring smooth performance without requiring heavy JavaScript libraries. Also the torus is a reference to the Big Bang. We used AI prompting to design this rotating torus and took inspiration from our design of our logo.




Typography: follows the same rules as Apple's Design System, with system fonts utilized in a manner familiar to users across different operating systems (`-apple-system`, `BlinkMacSystemFont`, `system-ui`). This approach achieves coherence in rendering with best readability, while the modern feel is preserved.




Below the hero section, we implemented three feature cards that showcase the core functionality: AI-powered matching, email drafting, and lab browsing. These cards use a gradient background system (blue-to-purple) that matches our overall color scheme, with each card having a distinct gradient variant to create visual hierarchy. We included short and cute emoji icons with custom SVG graphics to maintain a professional appearance while preserving the visual communication of each feature's purpose and appealing to younger generations with the usage of emojis.




The statistics section provides concrete metrics about the platform's scope, highlighting the number of institutions and labs available. This section uses a blue-to-purple gradient for headings and numbers, reinforcing the brand identity while making key information stand out and providing a “cool” factor. The "Browse Labs" call-to-action at the bottom serves as a natural progression point for users who have scrolled through the entire homepage, indicating they're ready to explore available opportunities and allowing the user to follow a very logical point.




Logo Design: The Insight Ring




The RIQ logo evolved from an initial magnifying glass concept to an "Insight Ring" design—a clean torus/ring. The logo features three to four small orbiting dots that animate around the ring, creating a sense of movement and discovery. This design metaphorically represents the process of finding insights (the ring) through exploration (the orbiting dots), perfectly aligning with the platform's mission of connecting students with research opportunities. We used AI prompt to design this clean torus ring.




The logo features a blue-to-purple gradient with glow effects that create a sense of depth and will contrast crisply against a dark background. The gradient and glowing are achieved using CSS filters and SVG gradients for scalable, crisp rendering at any size.




A note to add is that the torus is a reference to the Avengers Infinity War spaceship taken by one of Thanos’s right men and is the fight scene and has a deeper meaning with the Avengers and this sense of community as well as empowerment to make a difference within the world.




Technical Architecture




Flask as Backend Framework




We chose Flask as our web framework for its simplicity, flexibility, and Python-native ecosystem. Flask's lightweight nature allows for rapid development while providing all necessary features for a web application of this scope. The framework's routing system cleanly separates different application features, making the codebase maintainable and easy to extend.




The application follows a traditional Model-View-Controller (MVC) pattern, with database models defined using SQLAlchemy, route handlers in `app.py`, and presentation logic in Jinja2 templates. This separation of concerns makes the codebase easier to understand, test, and modify.




Database Design: SQLite with SQLAlchemy ORM




We use SQLite as the engine of our database, which is perfect for development and small-to-medium scale deployment. SQLite does not require a separate server process and simplifies deployment, with excellent performance for the typical read-heavy workload of a lab matching platform.




The five main objects of the database schema are:




1. **User**: Stores information on accounts such as username, e-mail, and password hash. Passwords are stored securely with Werkzeug's password hashing using `pbkdf2:sha256` with Python 3.9 compatibility.




2. **SavedPI**: Keep track of what PIs each user has saved, unique constraint on the combination so users can build a list of their own labs.




3. **Resume**: It stores uploaded resume files and their extracted text content. The extracted text is very important for AI matching to give proper context on the student's background, skills, and experience.




4. **UserProfile**: This includes other user information like the major field, year in school, research interests, and preferred techniques. The data further refines the accuracy of the matching algorithm by providing structured information.




5. **PasswordResetToken**: Secure password reset token using one-time, time-limited tokens. Tokens expire after an hour and are flagged as used upon password reset to prevent replay attacks.




Migration logic for schema changes, gracefully handling additions of new columns-such as `username` and `year_in_school` to existing tables-is encapsulated in the initialization of this database.




Integration: AI - OpenAI GPT-4o-mini




The application makes use of OpenAI's GPT-4o-mini model for two primary functions: lab matching and email generation. We chose GPT-4o-mini over larger models because it is greatly cost-effective and the cheapest model, enabling the application to be economically viable while sustaining high-quality outputs.




Lab Matching Algorithm




The matching algorithm processes faculty data in parallel batches to optimize performance. Instead of evaluating labs sequentially (which would take minutes), we split the faculty list into batches of 10 labs each and process up to 100 labs using Python's `ThreadPoolExecutor`. This parallel processing approach reduces matching time from several minutes to under 30 seconds for typical workloads.




The matching prompt instructs the AI to score each lab based on multiple criteria: 40% research area match, 25% skills alignment, 15% academic level appropriateness, 10% department fit, and 10% research impact (H-index). The AI returns a JSON array with PI IDs, scores (0-100), and brief reasoning for each match. We filter out matches below 50 and rank results from highest to lowest score.




The algorithm uses a low temperature setting of 0.2, ensuring consistent and reliable scoring across multiple runs. This deterministic approach is critical for user trust—students must get similar results when they rerun matches with the same resume.




Email Drafting System




The email drafting feature produces personalized cold emails by combining information from PI, student background, and optional research interests. The system emphasis is on natural, conversational tones.
The instructions include details for email structure: subject line, greeting, body paragraphs, closing, and tone: warm but professional, specific but not gushing, confident but humble.
Frontend Implementation
#### CSS Architecture: Design System with CSS Variables




This design system relies on CSS custom properties (variables) in this stylesheet to achieve consistency in design. This allows for color definition centralization, spacing, typography, and animation timing, making it very easy to maintain visual consistency or implement theme changes. The variable system includes




- Background colors at various elevation levels (`--bg`, `--bg-elevated`, `--bg-card`)




- Accent colors with variants (`--accent`, `--accent-soft`, `--accent-hover`)




Text colours for different emphasis levels (`--text-main`, `--text-muted`, `--text-dim`)




Border radius and shadow definitions for consistent styling




- Transition timing for smooth animations




Most of it was designed using a combination of Figma, our own designation of CSS and some AI prompting to amplify the code.




#### Responsive Design and Animations




It uses CSS Grid and Flexbox for responsive layouts on various screen sizes. For AI prompting to make the homepage look cool, our key animations are:




- **Torus Rotation**: This is achieved through CSS using `@keyframes` with `transform: rotateY()` to apply the effect of rotation in 3D space. Animation is looped on the homepage.




- **Gradient Wave Background**: Non-homepage pages feature an animated blue-purple gradient that moves in a wave-like motion. This is achieved using multiple layered gradients with `@keyframes` animations that shift gradient positions, creating a flowing, organic movement pattern.




- **Black Hole Graphic**: The email drafting page includes an animated black hole visualization with accretion rings and twinkling stars. This uses CSS animations to create rotating rings and pulsing effects, reinforcing the space/galaxy theme.




- **Loading Indicators**: AI processing operations show animated thinking dots and progress bars to provide user feedback during possibly long-running operations.




Security Changes




Session Management




Flask sessions use a secret key to cryptographically sign session cookies, making them tamper-safe. The session stores only the user ID, reducing the risk if session data is intercepted.




Security of File Upload




Uploaded files are validated for allowed extensions (PDF and DOCX only) and sanitized using `secure_filename()` to prevent path traversal attacks. Files are stored with user-specific prefixes to prevent conflicts and unauthorized access.




Password Reset Security




Password reset tokens are generated using `secrets.token_urlsafe()`, which generates cryptographically secure random tokens. Tokens expire after one hour and are single-use, preventing replay attacks. The token generation and verification functions include comprehensive error handling to prevent timing attacks.




Performance Optimizations




Parallel Batch Processing




The most significant performance optimization performed is the parallel batch processing for lab matching. Using `ThreadPoolExecutor`, we accelerated the process by processing several batches simultaneously.




Page-by-Page Design Decisions




LABORATORIES Browse Labs (General Page)




The general browse page features a Harvard-inspired Faculty Program in Neuroscience-style filter system, offering recognizable interaction patterns for users accustomed to searching academic laboratory lists. TO the left it contains filters for institution, field, techniques, and location, which allows users to speedily narrow down results to their preferences.
Above is a page that lists PIs in a tabular form, with columns for logo, professor name, information, email, H-index, and actions. The H-index gives an easy measure of the impact of research, including prestige, so users can identify well-established researchers.




We Googled and determined our best course of action was to implement AJAX for the save functionality to avoid having the page reload and lose scroll position—a huge UX improvement, especially on pages with very long lists of results.




My Matches Page




The Matches page is the core feature of the application, which displays AI-ranked lab matches based on the user-uploaded resume. It displays match scores (0-100) along with brief reasoning for each match to help users understand why certain labs are recommended.




Saved PIs Page The saved PIs page aggregates all the labs a user has expressed interest in. It offers expanded information compared to the matches page, such as full research descriptions and the techniques used within each lab. Users are able to compare selected labs with each other, export the results as PDF, and remove PIs from their list of saved PIs. The comparison aspect enables users to evaluate multiple labs side by side to make informed decisions on the opportunities they decide to pursue. The PDF export functionality enables offline review and sharing with advisors or mentors. Email Drafting Pages The single email drafting page features a two-column layout: form inputs on the left and an animated black hole graphic on the right. This layout balances functionality with visual interest and makes the email generation process engaging. The form only shows saved PIs in the dropdown, ensuring users draft emails for labs they've already expressed interest in. This design choice prevents users from drafting emails to labs they haven't properly evaluated, improving email quality and reducing spam. The bulk email page uses a checkbox interface for selecting multiple PIs, with the same visual design as the single email page for consistency. Help Page The help page is both documentation and a way to obtain feedback. It contains guides on how to use each feature in the application, FAQs compiled from test users and actual PIs/grad students, and tips on how to get into research. There's also a form at the bottom for the user to report any issues or suggest an improvement. We could enhance the help page with direct email contact functionality, but the current feedback form provides a sufficient mechanism for user communication during the development phase. Account/Profile Page The account page shows user profile information along with the progress bar visualization regarding the completeness of their profiles. As a gamification component, this motivates users to provide full information, leading to more accurate matches. The page enables updating the user's profile information, including the major field, year in school, research interests, and preferred techniques.








