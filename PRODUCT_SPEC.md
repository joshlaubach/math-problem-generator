# Product Spec: AI Math Tutor Platform

**Version:** 1.0  
**Date:** June 2026  
**Author:** Josh Glaubach  
**Status:** Pre-launch (private beta target: August 2026)

---

## Overview

This is an AI-powered math tutoring platform that delivers the experience of a skilled private tutor — not a homework tool. The product is built around a single differentiating interaction: a student works through a problem, and an AI tutor watches what they draw, identifies where their reasoning breaks down, and guides them toward the answer through Socratic questions rather than giving it away. The platform is aimed at high school and college students working through math courses who want something meaningfully closer to a real tutoring session than a chat window.

The product has two modes that serve different intent: a standalone **Problem Generator** for self-directed practice, and live **AI Tutor Sessions** that replicate the rhythm of a human tutoring session — session opening, problem solving, real-time feedback, and a closing summary with next steps.

Revenue goal: $10k/month net by December 31, 2026. Public launch mid-August 2026.

---

## Problem

Private math tutoring is effective but expensive and geographically constrained. AI chat tools can explain math but they fail at the actual job of tutoring — which is not explaining concepts, it is diagnosing where a specific student's understanding breaks down and addressing that specific thing. Current AI tools:

- Give answers instead of guiding toward them, producing the illusion of learning
- Cannot see a student's work-in-progress to catch mistakes as they form
- Have no memory of prior sessions, so they can't track which misconceptions keep recurring
- Respond to "I don't get it" with a comprehensive explanation instead of a targeted diagnostic
- Have no structure: no session opener, no goal-setting, no closing summary with homework

The core product claim is: this platform does not produce a better explanation than a textbook. It produces a better tutor than most students can access.

---

## Who It's For

**Primary:** High school students in Algebra through Calculus, and college students in Calculus, Linear Algebra, Differential Equations, and Statistics. Students who are actively enrolled in a course, have upcoming tests or assignments, and want structured help — not just content lookup.

**Secondary:** Teachers who want to create and assign practice problems for their classrooms, and track per-student performance by topic.

**Not primary:** Students looking for a homework completion tool, or students who want answers without engagement. The product explicitly refuses to give answers without work, and this is a feature.

---

## Curriculum Scope

The platform covers math from Pre-Algebra through advanced undergraduate coursework across 14 courses:

- Pre-Algebra, Algebra 1, Geometry, Algebra 2/Trigonometry
- Pre-Calculus, AP Calculus AB, AP Calculus BC
- Multivariable Calculus, Linear Algebra, Differential Equations
- Statistics, Discrete Math, Proof Writing, Number Theory

Each course is broken into Units and Topics (e.g., Algebra 1 → Solving Equations → Two-Step Equations with Variables on Both Sides). The full curriculum lives in code as typed Python dataclasses, not in the database, which makes it fast to extend and impossible to corrupt with bad migrations.

---

## Core Features

### 1. AI Tutor Session

The primary product. A student starts a session by selecting a topic from the curriculum or uploading a problem set. Sessions run for one or two hours and are purchased as credits.

**What happens in a session:**

**Opening.** The tutor opens with a diagnostic or a review of the previous session — not immediately new material. On a student's first session on a topic, the tutor gives a short sequence of problems in escalating difficulty to find the ceiling of their current understanding. On subsequent sessions, the tutor opens with one problem from the prior session's assigned practice before moving forward.

**Problem solving.** The tutor presents problems one at a time. The student can respond in two ways: drawing on the shared whiteboard, or typing symbolic steps in the LaTeX input panel. Both routes feed the same tutor logic.

**Real-time feedback.** When the student pauses for 1.5 seconds after drawing, the canvas snapshot is sent to the backend. Claude Vision analyzes the work and returns a Socratic response: a guiding question, a targeted correction placed next to the mistake on the whiteboard, or a confirmation that the step is correct and a prompt for the next one. The tutor never completes the problem for the student.

**Hint escalation.** If a student is stuck, they can request a hint. Each topic has a pre-generated four-tier hint ladder (most indirect → most direct). A student requesting more than two hints on the same step triggers a short lesson sequence rather than more hints.

**Adaptive difficulty.** After three correct problems in a row, the tutor proposes harder problems and records a mastery gain. After two wrong answers in a row, it steps down one difficulty level and, if the failure pattern suggests a foundational gap, pivots to the Teaching Agent to deliver a targeted lesson before returning to practice.

**Closing.** At session end, the student sees a summary screen: topics covered, which problems they solved independently vs. with help, specific misconceptions identified by name (e.g., "sign error when distributing negative"), and a set of practice problems to work before the next session. The summary is emailed to the student. Teachers in a classroom plan receive per-student performance updates automatically.

### 2. Interactive Whiteboard

The whiteboard is the core interaction surface. It has two layers that share the same canvas:

**Tutor layer.** The tutor writes KaTeX-rendered math on this layer, animated with GSAP typewriter reveal. When the student makes an error, the tutor places an annotation — a correction or a question — spatially adjacent to the mistake, not as a chat message. When delivering a worked example, the tutor writes each step sequentially with 600ms between steps. Function graphs render inline using Mafs.

**Student layer.** A Fabric.js canvas overlaid on the tutor layer. The student draws freehand here using a pen or stylus (or mouse). A MathLive input field at the bottom of the whiteboard accepts typed LaTeX expressions for students who prefer symbolic input. Student drawings are checkpointed as base64 images every 30 seconds.

The spatial relationship between tutor annotations and student work is intentional: the tutor responds where the student made the mistake, not in a separate panel. This is the closest an AI tool can get to the experience of a tutor circling something on a paper.

### 3. Problem Generator

The entry-level product, available on a lower subscription tier or for free with a problem cap. Students and teachers browse the curriculum and generate practice problems on any topic at any difficulty level (1–5).

Problems are generated using a solution-first pipeline: the system picks a target answer, builds the equation around it, verifies it with SymPy for mathematical validity, and then sends it to Claude to wrap in a word problem context. This prevents problems with no solution, contradictory constraints, or answers that don't simplify cleanly.

Generated problems include a step-by-step solution and a four-tier hint ladder. Students can work through them in a lightweight practice interface (no whiteboard, no AI chat) or save them to a problem set.

Teachers can generate problem sets, configure difficulty, and assign them to classrooms with due dates.

### 4. Teacher Tools

Teachers can create a classroom, add students via invite code, assign problem sets with deadlines, and view a per-student performance dashboard. The dashboard shows mastery scores by topic (derived from completed sessions and practice), identifies which students are below threshold on which concepts, and surfaces the most common misconceptions across the class.

This is a secondary surface — the primary user is the student, and teacher tools exist to make the platform adoptable by schools and tutoring centers rather than only direct-to-consumer families.

---

## Session Tutor Behavior: Design Principles

The AI tutor is designed around a specific set of behavioral constraints derived from how effective human tutors work. These are implemented as system prompt rules enforced across all tutor interactions.

**Socratic by default.** The tutor asks questions before it explains. The first response to a wrong answer is always a question that points toward where the error occurred, not a correction. The tutor only explains after the student has confirmed they cannot self-correct.

**One question per message.** The tutor never asks more than one question at a time. Students answer the easiest one and ignore the rest. Single questions produce more information.

**Work required, not just answers.** The tutor refuses to evaluate a bare answer without seeing the steps. "Walk me through how you got that" is the default response to a correct bare answer, and "I need to see your steps to tell you if it's right" is the default for an incorrect one.

**Never confirm understanding with words.** When a student says "I get it," the tutor gives a follow-up problem. Always. "I understand" does not mean the student can execute.

**Representation switching.** If the same explanation fails twice, the tutor switches approaches rather than rephrasing. The sequence: procedural → numerical example → conceptual (why it works) → Socratic (question-guided discovery) → decompose to prerequisites. Same explanation three times in a row means it will never work.

**Signal reading.** The tutor interprets message length and content as signals. Very short replies after a wrong answer (one or two words) trigger a single, narrow question about the most likely confusion point, never a re-explanation. Long messages with multiple questions get one answered first, explicitly deferring the others.

**Tone: warm, direct, honest.** No hollow praise ("Great question!"), no apologizing for the student's confusion, no "I know you can do this!" The tone is the best math teacher a student has ever had: they treat the student like an intelligent person who needs specific help with specific things. Wrong answers are handled matter-of-factly.

---

## Adaptive Engine

The platform tracks each student's mastery score per topic across sessions. The adaptive engine influences three things:

**Difficulty selection.** Each session starts at the student's last recorded mastery level for the topic. As the session progresses, the engine adjusts up or down in real time (±0.1 mastery per outcome, clamped to ±0.15 per session to prevent runaway drift).

**Spaced repetition scheduling.** Topics the student has worked on but not mastered are scheduled for review. The review interval is proportional to the mastery score — a topic at 0.4 mastery comes back sooner than a topic at 0.8. This is computed server-side and surfaced as a "Review due" badge on the curriculum browser.

**History briefing.** At the start of each session, the tutor is given a brief of the student's last three sessions: topics covered, weak concepts identified, and current mastery scores. This brief is injected into the system prompt, not shown to the student. The result is that the tutor opens with specific awareness of where the student has historically struggled — the equivalent of a tutor reviewing their notes before a session.

---

## Tutor Personas

Students select a tutor persona at their first session. Six personas are available (James, Isaac, Robert, Sarah, Emily, Natalie), each mapped to a distinct TTS voice. The persona is cosmetic in the initial release — the system prompt is identical, with only the tutor's name injected at render time. Future releases may differentiate explanation style (more formal, more conversational) by persona.

The default persona during private beta is Josh, which reflects the platform's origin as a solo practice and provides a recognizable identity during early user testing.

---

## Pricing

**Pack (on-ramp):** ~$35 for a single session credit. Designed to be the first-purchase path. After use, the post-session summary screen presents a membership CTA with the $35 credited toward the first month.

**Membership — Standard ($99/month):** Includes N tutor session credits + unlimited problem generation. Credits roll over one month. This is the primary product and the default CTA everywhere.

**Membership — Honors ($149/month):** More session credits per month, same model. For families with heavier tutoring needs.

**Classroom (TBD):** Teacher-facing tier. Priced per seat or per classroom. Deferred until after public launch.

Credits are consumed at WebSocket connection start. The session commitment screen — a modal with three checkboxes the student must confirm before the connection opens — ensures students are not billed without explicitly acknowledging the cost.

---

## Launch Sequence

**L0 — Production infrastructure (~1 week):** Railway API deployment, Vercel frontend, managed Postgres and Redis, Clerk production auth, Stripe test-mode checkout. Migrate 866 topic lessons currently in local files into the production database. Enable spend caps and billing alerts.

**L1 — Launch-cut engineering (~2–3 weeks):** Remove the `PAID_TIERS` access gate (credits-only access going forward); problem cache table with cross-student reuse and per-student deduplication; mastery persistence with all session exit paths (solved / timeout / disconnect); voice cost controls (per-session character budget, daily user cap); 13+ age attestation at signup; admin transcript viewer; failed-session auto-refund (credit restored if session ends due to server error or disconnects before threshold); mobile viewport gate for tutor sessions (tablets and computers only; practice works on mobile); Stripe subscription billing including renewal webhooks, dunning, cancel flow, and pack-to-membership credit.

**L2 — Architecture refactor (~1–2 weeks):** Characterization test suite for the WebSocket session (one test per message type, three stateful flows, LLM mocked) before touching anything. Extract all business logic out of `ws_router.py` into a clean `orchestrator.py`. Re-run live audit scripts after refactor. Layer in streak rules, background problem pre-generation, and spaced repetition on the clean structure.

**L3 — Private beta (~2–3 weeks):** Three to six real students, free credits, no public sign-up. Read every session transcript. Measure cost-per-session against the $35 pack math. Exit criteria: 10 clean sessions, cross-session memory visibly working, measured cost/session viable. Draft ToS, refund policy, and support flow during beta.

**L4 — Public launch.** Stripe live mode. Fast-follow: practice subscription tier, parent credit gifting, whiteboard agent improvements.

---

## Non-Goals (Current Scope)

The following are explicitly deferred until after public launch revenue is established:

- Affect monitoring (detecting frustration or disengagement from conversation patterns)
- Graphing agent (live interactive Desmos integration)
- Diagram generation (geometric figures, visual proofs)
- Parent reporter (weekly progress emails to parents separate from session summaries)
- Under-13 accounts (parent-initiated flow with COPPA-compliant data handling)
- Handwriting simulation on the tutor whiteboard layer
- Paid advertising (vetoed until LTV/churn numbers from beta justify edtech CAC)

---

## Success Criteria

**Private beta exit:**
- 10 clean sessions logged where the student arrived unable to do a problem type and left able to do it
- Cross-session memory visibly surfacing historical weak concepts in session openings
- Cost-per-session at or below the math that makes the $35 pack viable ($35 revenue → ~40% margin floor)
- Zero sessions that ended due to tutor giving away an answer unprompted

**Public launch (90-day post-launch):**
- 35–40 net new paid households per month
- Membership conversion rate from pack purchases > 40%
- Session completion rate (student does not disconnect early) > 75%
- Repeat session rate within 30 days > 60%

**December 31, 2026:**
- $10k/month net revenue (~165 active member households at blended $99–$149/month)
- A tutoring product Josh would watch a session replay of and be comfortable with what he sees
