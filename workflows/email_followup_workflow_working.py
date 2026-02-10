"""
Email Follow-Up Workflow - Working Version with OAuth

Breaks the email follow-up process into 3 manageable steps:
1. Analyze Contacts & History
2. Draft & Review Emails
3. Send Emails & Update Sheet

Uses the email_followup_agent which has OAuth configured.
"""

from agno.workflow import Workflow, Step
from email_followup import email_followup_agent

email_followup_workflow = Workflow(
    name="Email Follow-Up Manager",
    description="""
    Automated email follow-up workflow for sales contacts.

    **How it works:**
    - Step 1: Reads Google Sheet, identifies contacts needing follow-up (7+ days), checks Gmail history
    - Step 2: Drafts personalized emails based on history, shows for your approval
    - Step 3: Sends approved emails, updates Google Sheet with new contact dates

    **OAuth-enabled:** Works with your Google Sheets and Gmail credentials.

    **What you need:**
    - Google Sheet with columns: Name, Email, Company, Last Contact Date, Notes, Status
    - Gmail access for checking history and sending emails
    """,
    steps=[
        # ═══════════════════════════════════════════════════════════════
        # STEP 1: Analyze Contacts & Check Gmail History
        # ═══════════════════════════════════════════════════════════════
        Step(
            name="Analyze Contacts & History",
            agent=email_followup_agent,
            description="""
            **STEP 1 of 3: Analysis Phase**

            Your specific tasks for THIS step only:

            1. **Get Google Sheet URL** (if user hasn't provided it)
               - Ask: "Please share your Google Sheet URL"
               - Extract the spreadsheet ID from the URL

            2. **Read the Google Sheet**
               - Use read_sheet tool
               - Expected columns: Name, Email, Company, Last Contact Date, Notes, Status

            3. **Filter contacts needing follow-up**
               - Identify contacts where "Last Contact Date" is 7+ days ago
               - Skip contacts with Status = "followed up" or "closed"
               - Tell user: "Found X contacts needing follow-up"

            4. **Check Gmail history for EACH contact**
               - Use get_emails_from_user tool
               - COMMUNICATE: "Checking Gmail for [name] ([email])..."
               - Note key discussion points from previous emails
               - COMMUNICATE: "Found X emails" or "No previous emails found"
               - Show progress: "Checked 2 of 5 contacts..."

            5. **Summarize findings**
               - List each contact with brief context
               - Example: "John Doe (john@company.com) - Last contact 10 days ago, discussed pricing in previous email"

            **IMPORTANT:**
            - STOP after completing this analysis
            - Do NOT draft emails yet (that's Step 2)
            - End with: "Analysis complete. Ready to draft emails in Step 2."
            """,
        ),

        # ═══════════════════════════════════════════════════════════════
        # STEP 2: Draft Emails & Get Approval
        # ═══════════════════════════════════════════════════════════════
        Step(
            name="Draft & Review Emails",
            agent=email_followup_agent,
            description="""
            **STEP 2 of 3: Drafting Phase**

            Context from Step 1: You analyzed contacts and checked their Gmail history.

            Your specific tasks for THIS step only:

            1. **Ask about template preference**
               - "Would you like to:"
               - "A) Use your own template for all contacts"
               - "B) Let me draft personalized emails based on their history"

            2. **Draft personalized emails**
               For each contact from Step 1:
               - Keep under 100 words
               - Professional but friendly tone
               - Reference specific details from their previous conversations
               - Include clear call-to-action (meeting, demo, call)
               - Craft engaging subject line (under 50 characters)

            3. **Present ALL drafts clearly**
               Format:
               ```
               ═══════════════════════════════════════
               Email 1 of N
               ═══════════════════════════════════════
               To: [Name] <[email]>
               Subject: [subject line]

               [email body]

               ───────────────────────────────────────
               Action needed: APPROVE / EDIT / SKIP
               ═══════════════════════════════════════
               ```

            4. **Get approval for EACH email**
               - Wait for user to respond with APPROVE, EDIT, or SKIP
               - If EDIT: Get their edits and update the draft
               - If SKIP: Mark as skipped, move to next
               - Track which emails are approved for sending

            5. **Confirm approved emails**
               - List all approved emails
               - Example: "Ready to send 8 of 10 emails (2 skipped)"

            **IMPORTANT:**
            - STOP after getting all approvals
            - Do NOT send emails yet (that's Step 3)
            - End with: "Drafts approved. Ready to send in Step 3."
            """,
        ),

        # ═══════════════════════════════════════════════════════════════
        # STEP 3: Send Approved Emails & Update Sheet
        # ═══════════════════════════════════════════════════════════════
        Step(
            name="Send Emails & Update Sheet",
            agent=email_followup_agent,
            description="""
            **STEP 3 of 3: Execution Phase**

            Context from Step 2: You have approved email drafts ready to send.

            Your specific tasks for THIS step only:

            1. **Send approved emails**
               - Use send_email tool for EACH approved email
               - Send one at a time (not batch)
               - COMMUNICATE after each: "✓ Sent email to [name]"
               - If send fails, note the error and continue with others

            2. **Update Google Sheet**
               For each successfully sent email:
               - Use update_sheet tool
               - Set "Last Contact Date" to today's date (YYYY-MM-DD)
               - Set "Status" to "followed up"
               - COMMUNICATE: "✓ Updated sheet for [name]"

            3. **Final summary**
               Report:
               - Total emails sent: X
               - Total sheet updates: X
               - Failed (if any): X with reasons
               - List of all contacts successfully followed up

               Example:
               ```
               ═══════════════════════════════════════
               Email Follow-Up Complete!
               ═══════════════════════════════════════
               ✓ Sent 8 emails
               ✓ Updated 8 rows in Google Sheet

               Contacts followed up:
               1. John Doe - john@company.com
               2. Jane Smith - jane@company.com
               ...

               Next follow-up due: [7 days from today]
               ═══════════════════════════════════════
               ```

            **IMPORTANT:**
            - This is the final step
            - End with clear confirmation of completion
            - Provide actionable next steps if needed
            """,
        ),
    ],
)
