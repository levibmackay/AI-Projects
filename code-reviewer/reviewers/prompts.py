SYSTEM = """You are a senior software engineer with 15 years of experience across multiple languages and domains. You give direct, specific, actionable code reviews. You don't pad reviews with generic advice. Every point you make is grounded in the actual code provided."""

FULL_REVIEW = """Review this {language} code thoroughly.

```{language}
{code}
```

Structure your review exactly like this:

SCORE: x/10

SUMMARY
2-3 sentences on the overall quality and biggest issues.

BUGS
List every bug, logic error, off-by-one, null/undefined risk, or incorrect assumption. For each one: what it is, why it breaks, and how to fix it with a corrected code snippet.
If none found, say "No bugs found."

SECURITY
List every security issue: injection risks, hardcoded secrets, unsafe deserialization, missing auth checks, insecure defaults, etc. Rate each as CRITICAL / HIGH / MEDIUM / LOW.
If none found, say "No security issues found."

PERFORMANCE
Call out inefficient algorithms, N+1 queries, unnecessary recomputation, blocking I/O, memory leaks, or anything that will hurt at scale.
If none found, say "No performance issues found."

CODE QUALITY
Comment on: naming, structure, duplication, overly complex logic, missing error handling, poor abstractions, inconsistent style.

TOP 5 IMPROVEMENTS
Numbered list. Each improvement should be specific and include a before/after code example where it helps."""


QUICK_REVIEW = """Give me a fast, punchy code review of this {language} code.

```{language}
{code}
```

Score it x/10. Then give me the top 3 issues in order of severity with a one-line fix for each. Keep it under 200 words total."""


SECURITY_REVIEW = """You are a security-focused code reviewer. Perform a security audit on this {language} code.

```{language}
{code}
```

For every issue found, structure it as:

[SEVERITY] Issue Name
What it is: ...
Where: line / function / variable
Why it matters: ...
Fix:
```
corrected code here
```

Cover: injection (SQL/command/LDAP), XSS, CSRF, insecure deserialization, broken auth, sensitive data exposure, hardcoded secrets, path traversal, XXE, insecure direct object references, security misconfigurations.

End with an overall security score from 1-10 and a one-paragraph summary."""


PERFORMANCE_REVIEW = """Analyze this {language} code purely for performance issues.

```{language}
{code}
```

For each issue found:
- What is inefficient
- Why it matters (time/space complexity, I/O, memory)
- Optimized version with code example

Include Big O analysis where relevant. End with an overall performance score from 1-10."""


ROAST = """Roast this {language} code like a brutal senior dev who has seen too much bad code. Be funny but make sure every criticism is technically valid and comes with a real fix. Don't hold back.

```{language}
{code}
```

After the roast, give a "Redemption Arc" section with the 3 most important fixes."""


CHAT_SYSTEM = """You are a senior software engineer helping a developer understand and improve their code. The developer has already submitted their code for review. Answer their follow-up questions directly and specifically. Reference the actual code when possible. Keep answers concise but complete. Include code examples when helpful."""


EXPLAIN_ISSUE = """Given this {language} code:

```{language}
{code}
```

Explain this specific issue in plain English, then show exactly how to fix it:

Issue: {issue}"""


MULTI_MODEL_MERGE = """You have received code reviews from multiple AI models. Synthesize them into one final review.

{reviews}

Produce a merged review that:
1. Highlights issues that multiple models agreed on (these are almost certainly real)
2. Includes unique valid points from individual models
3. Resolves any contradictions by picking the most technically sound position
4. Gives a final consensus score from 1-10

Keep the same structure: SCORE, SUMMARY, BUGS, SECURITY, PERFORMANCE, CODE QUALITY, TOP 5 IMPROVEMENTS."""
