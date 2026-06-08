# Trigger eval — `bitrix24-agent` description

DEV/QA artifact (not loaded by the skill). The `description` is the only selection signal,
so after any description change, sanity-check triggering with this set. Per the Agent Skills
best-practice loop:

- **Method.** Paste ONLY the current `description` (from `SKILL.md` frontmatter) into a fresh
  agent session and ask it, for each query below, whether it would invoke this skill (author in
  one session, test in a separate fresh one). Run each query ~3× and take the majority.
- **Targets.** ≥90% of should-trigger fire; ≥90% of should-NOT-trigger correctly abstain.
- **The near-miss negatives are the valuable ones** — they share keywords (CRM, deal, lead,
  chat, OAuth, duplicates, calendar) but need a *different* tool. Obvious negatives
  ("write a fibonacci function") test nothing.

## should_trigger (expect: invoke)

1. Create a lead from this web-form submission in our CRM portal.
2. Sync the latest deals from the portal and update their stages.
3. Find duplicate contacts by phone number before I add this one.
4. Log a call activity on this contact's timeline.
5. Move deal 742 to the "Won" stage.
6. Generate an invoice for this deal.
7. Send a chat message / notification to user 12 in our portal.
8. Build a chat-bot that answers a slash command.
9. Set up reliable offline event sync for CRM updates.
10. I'm getting QUERY_LIMIT_EXCEEDED / WRONG_AUTH_TYPE — help me fix the integration.
11. Connect our AI assistant to Bitrix24 over a webhook.
12. Upload a file and attach it to a task linked to a deal.

## should_NOT_trigger (near-misses — expect: abstain, route elsewhere)

1. Create a deal in Salesforce. *(other CRM)*
2. Clean up duplicate contacts in HubSpot. *(other CRM)*
3. Open a ticket in Jira / transition it to In Progress. *(issue tracker)*
4. Post a message to the #incidents Slack channel. *(Slack, not Bitrix chat)*
5. Sync these leads to Pipedrive. *(other CRM)*
6. Add a lead in amoCRM. *(other CRM)*
7. Create an event in Google Calendar. *(different calendar API)*
8. Set up OAuth for the Google Drive API. *(OAuth, but not Bitrix)*
9. Find duplicate rows in this CSV file. *(dedup, but no CRM/portal)*
10. Write a generic Python REST client with retry/backoff. *(plumbing, no Bitrix target)*
11. Manage issues and cycles in Linear. *(issue tracker)*
12. Draft a quote in Zoho CRM. *(other CRM)*

## Notes
- If a should-NOT-trigger near-miss fires, tighten the description's exclusion clause
  (it already excludes Salesforce/HubSpot/amoCRM/Pipedrive/Zoho).
- If a should-trigger misses, make the description "pushier" / add the missing trigger phrase
  (front-load it — descriptions get truncated under context pressure).
