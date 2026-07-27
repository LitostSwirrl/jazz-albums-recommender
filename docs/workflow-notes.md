# Workflow orchestration notes

Practices for running subagent-driven work on this project faster without
lowering the quality bar. Written 2026-07-27 from the recs-pipeline branch
(Plan 1, Tasks 1-11), using measured cycle times rather than impressions.

Each practice states what to do, why, and the evidence that produced it. If a
practice ever costs more than it saves, delete it and note why — this file is
meant to be edited, not accumulated.

---

## 1. Check the premise before it becomes a requirement

Before writing any finding into a task brief, verify it against the actual data.
A few lines of Python against the caches, not reasoning from the output.

**Why:** a wrong premise costs an entire implement-review cycle, and the cost is
paid at the far end where it is most expensive.

**Evidence:** in the Task 11b brief, items 2 and 10 were validated first (the
merge rule was measured on the real pool, the allowlist and denylist keys were
computed with `common.norm_key`), and both landed clean. Item 11 was not
validated. It asserted that one Pitchfork box score was being copied onto two
albums; the review page in fact carries six per-album grades, correctly paired.
The change was specified, implemented, tested and reviewed before that surfaced.
The check that would have killed it was four lines and about two minutes.

**Corollary:** when a brief states a measured outcome, say what it was measured
over. Item 2's table was measured over the visible output; the implementer
correctly applied the rule over the pool and got 34 merges instead of 4. The
reviewer judged the implementer right. Ambiguity between "the rule" and "the
measurement" is the controller's defect, not the implementer's.

## 2. Parallelize review by lens, do not shorten it

Instead of one reviewer covering spec, quality and tests over a large diff,
dispatch concurrent reviewers with distinct lenses — spec compliance,
correctness on the risky path, test adequacy — and merge their reports.

**Why:** wall clock drops to the slowest reviewer rather than the sum. Different
lenses find different defects; running the same lens twice mostly does not.

**Cost, stated honestly:** more tokens. This buys speed with spend, not with
quality. Do not pretend otherwise when deciding.

**Evidence:** the single Task 11b reviewer took 8.5 minutes on a 66KB diff.

## 3. Tier the loop by risk, not by habit

- **Mechanical change, exact values specified in the brief:** implementer, then
  controller verification (tests, build, inspect the output). Fold the review
  into the next batch.
- **Judgment, shared derivation paths, or anything touching the integrity gate:**
  full loop — implementer, task review, fix rounds, scoped re-review.

**Why:** ceremony proportional to risk. Two allowlist entries do not need what a
427-line scoring change needs.

**Evidence:** Task 11c (two allowlist entries and one merge pair) received the
same treatment as Task 11a (six build changes to the scoring engine).

## 4. Front-load the full diagnostic battery before the first human gate

Run every check you intend to run — concentration statistics, duplicate scans,
data-quality audits, grounding spot-checks — before the first review with a
human, not after their first round of feedback.

**Why:** each human gate is a full turnaround. Thoroughness in round 1 collapses
rounds.

**Evidence:** taste-gate round 1 presented tables and produced four decisions.
Round 2 presented tables plus concentration stats, a duplicate scan, a year
audit and a comp audit, and produced eight. Round 3 was cheap because round 2
was thorough. The diagnostics were available before round 1.

## 5. Two agent-reliability plays, both proven

**On a stall:** verify the working tree yourself, then resume the agent with its
exact state spelled out — what is already done, what is not, what is
uncommitted. Do not restart from scratch.
*Evidence:* the Task 11a fix agent stalled at the 600s watchdog having completed
one of two findings. Resuming with verified state recovered the work; a restart
would have redone it.

**Before dispatching an implementer:** check whether one is already running for
the same task.
*Evidence:* Task 8 had two implementers land competing commits (`2f88c50` and
`a07b2d5`) because a background agent was already working when the session
dispatched its own. The net diff was coherent, but it left a duplicated commit
and a mismatched trailer that are still deferred to the merge.

## 6. Triage minors at the time, not all at the end

When a review defers a Minor, rule on it immediately — fix now, defer with a
reason, or won't-fix — so the final whole-branch review inherits a curated list.

**Why:** a large undifferentiated pile arriving at the last gate is a big-bang
risk at exactly the point where there is least appetite to act on it.

**Evidence:** roughly forty deferred minors accumulated across Tasks 1-11b, all
landing on one final review.

## 7. Log wall clock per task in the ledger

**Why:** everything above was reconstructed from timestamps that happened to be
noticed. Without measurement, bottleneck analysis is anecdote.

---

## What not to cut

These cost time and have each earned it:

- **The zero-hallucination integrity gate.** Preventive, so it looks idle. The
  Task 11b review traced it end to end and confirmed it still covers every album
  reaching disk after the cap and merge changed which albums get there.
- **Reviewers reproducing claims instead of trusting reports.** The Task 11a
  re-reviewer independently reproduced both experiments and confirmed the new
  test fails against the reverted derivation for the right reason. That is the
  difference between a fix that is real and one that is merely plausible.
- **Cache permanence in fetchers.** Three process deaths during the Reddit run
  (two machine sleeps, one reboot) cost zero data and zero re-extraction.
- **Controller first-hand verification.** Running the tests and inspecting the
  output personally, rather than accepting the implementer's report.
- **Committing the resume prompt the moment a scope decision arrives**, before
  any execution. The decision is perishable; execution inertia is real.
