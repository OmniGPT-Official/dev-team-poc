"""
HR Hiring Workflow — Deterministic 3-step pipeline for job posting.

Breaks the HR hiring process into 3 sequential steps:
1. Gather Requirements — HR Lead collects all job details from the user
2. Write Job Description — JD Writer produces bilingual JD (EN + Thai + HTML)
3. Post the Job — Job Poster publishes to the selected platform

Uses Agno Workflow + Step for deterministic execution (not Team delegation).
"""

from agno.workflow import Workflow, Step

from agents.hr_lead import hr_lead_agent
from agents.hr_jd_writer import hr_jd_writer_agent
from agents.hr_job_poster import hr_job_poster_agent

hr_workflow = Workflow(
    name="HR Hiring Pipeline",
    description="""
    Guided hiring workflow for companies in Thailand.

    **How it works:**
    - Step 1: HR Lead gathers all job requirements from you (title, responsibilities, location, salary, etc.)
    - Step 2: JD Writer creates a bilingual job description (English + Thai + HTML for Indeed)
    - Step 3: Job Poster publishes the listing to your chosen platform (Indeed Thailand, etc.)

    **What you need:**
    - Basic information about the role you want to fill
    - Preferred job board for posting (defaults to Indeed Thailand)
    - Application contact email
    """,
    steps=[
        # ═══════════════════════════════════════════════════════════════
        # STEP 1: Gather Requirements
        # ═══════════════════════════════════════════════════════════════
        Step(
            name="Gather Requirements",
            agent=hr_lead_agent,
            description="""
            **STEP 1 of 3: Requirements Gathering**

            Your specific tasks for THIS step only:

            1. **Greet the user** and explain you'll be collecting job details
               - Be friendly and professional — this should feel like talking to an HR expert

            2. **Collect all required information** (ask 1-2 questions at a time):
               - Job title (e.g. 'Padel Coach', 'Front Desk Staff')
               - Department or team
               - Key responsibilities (3-5 bullet points)
               - Required qualifications and skills
               - Location (city/area in Thailand)
               - Employment type: Full-time / Part-time / Contract
               - Number of positions available

            3. **Collect optional information** (ask if the user wants to provide):
               - Salary range (in THB, monthly)
               - Years of experience required
               - Nice-to-have skills
               - Work schedule (weekends, shifts, etc.)
               - Benefits (social security, health insurance, transport, meals)
               - Application deadline
               - Contact email for applications

            4. **Summarize everything** and ask user to confirm
               - Present a clear summary of all collected details
               - Ask: "Does this look correct? Any changes before I send this to the JD writer?"

            **IMPORTANT:**
            - STOP after the user confirms the requirements
            - Do NOT write the job description yourself (that's Step 2)
            - End with: "Requirements confirmed. Sending to JD Writer in Step 2."
            """,
        ),

        # ═══════════════════════════════════════════════════════════════
        # STEP 2: Write Job Description
        # ═══════════════════════════════════════════════════════════════
        Step(
            name="Write Job Description",
            agent=hr_jd_writer_agent,
            description="""
            **STEP 2 of 3: Job Description Writing**

            Context from Step 1: The HR Lead has gathered and confirmed all job requirements.

            Your specific tasks for THIS step only:

            1. **Review the requirements** from Step 1
               - Identify all details: title, responsibilities, qualifications, location, salary, benefits

            2. **Write the complete bilingual job description** with this structure:

               **ENGLISH VERSION**
               - Job title, company, location, employment type, salary
               - About the Role (2-3 sentences)
               - Key Responsibilities (bullet points)
               - Requirements (bullet points)
               - Nice to Have
               - What We Offer (include Social Security / ประกันสังคม)
               - How to Apply

               **THAI VERSION (เวอร์ชันภาษาไทย)**
               - Same structure in natural Thai (not word-for-word translation)

               **INDEED HTML VERSION**
               - Combined HTML using <h2>, <ul>, <li>, <p> tags only
               - Under 5000 characters

            3. **Present the full JD to the user**
               - Ask: "Here is the job description. Would you like any changes, or shall I proceed to post it?"

            4. **Handle revisions** if requested
               - Make edits as requested
               - Present updated version for approval

            **IMPORTANT:**
            - STOP after the user approves the JD
            - Do NOT post the job yourself (that's Step 3)
            - End with: "Job description approved. Ready to post in Step 3."
            """,
        ),

        # ═══════════════════════════════════════════════════════════════
        # STEP 3: Post the Job
        # ═══════════════════════════════════════════════════════════════
        Step(
            name="Post Job to Platform",
            agent=hr_job_poster_agent,
            description="""
            **STEP 3 of 3: Job Posting**

            Context from Step 2: The JD Writer has created an approved bilingual job description.

            Your specific tasks for THIS step only:

            1. **Ask which platform to post to**
               - Call `list_job_boards()` to show available configured platforms
               - Ask user: "Which platform would you like to post to?"
               - If user wants a non-configured platform and browser tools are available,
                 offer to use the managed browser

            2. **Confirm posting details**
               - Show: job title, platform, location, job type, salary, apply email
               - Ask: "Shall I proceed with posting?"

            3. **Post the job**
               - For configured platforms: use `post_job_to_board(...)`
               - For other platforms: use browser tools if available
               - If browser tools are not available, explain and suggest configured platforms

            4. **Report results**
               - Share the live job URL if available
               - Confirm the posting was successful

               Example:
               ```
               ═══════════════════════════════════════
               Job Posted Successfully!
               ═══════════════════════════════════════
               Platform: Indeed Thailand
               Job Title: [title]
               Location: [location]
               Status: Live
               URL: [job URL if available]
               ═══════════════════════════════════════
               ```

            **IMPORTANT:**
            - NEVER post without explicit user confirmation
            - If credentials are missing, tell the user to set them up
            - This is the final step — end with clear confirmation
            """,
        ),
    ],
)
