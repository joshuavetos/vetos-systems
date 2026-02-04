# Killing Bad Ideas Early

This work sample documents a real pattern in my work: identifying when an idea is becoming more elaborate instead of more useful, and deliberately stopping before it hardens into a system that can’t survive pressure.

## The Initial Problem

I was exploring how to reduce overconfident errors in large language model outputs—specifically hallucinations and authoritative-sounding false claims.

The initial question was straightforward:
How do you use AI productively without turning it into an authority you shouldn’t trust?

## The First Attempt (and Why It Failed)

The early iterations drifted toward a named framework with formal-sounding language, internal rules, and increasing structural complexity.

While it felt rigorous, this approach had clear failure modes:
- It incentivized consistency over correctness
- It discouraged disagreement by framing deviation as “incorrect execution”
- It created a narrative of control without operational guarantees

In short, it was becoming authority theater—a system that looked disciplined but didn’t actually constrain failure.

That was the signal to stop.

## How I Used AI in This Phase

I used LLMs aggressively to:
- expand the idea space quickly
- stress-test assumptions
- surface edge cases and contradictions

Crucially, I did not treat model output as truth.
I treated it as adversarial input—useful for finding weak spots, not for declaring conclusions.

## The Pruning Decision

Instead of refining the framework, I reversed direction and asked:
What is the smallest set of constraints that actually changes behavior?

Everything that did not directly enforce better decisions was removed.

This meant:
- deleting named systems
- deleting diagrams
- deleting “canon” language
- deleting anything that couldn’t be tested or enforced

What remained was not a framework, but a handful of rules.

## What Survived

The useful core condensed into a small set of operating constraints:
- Prefer abstention over guessing on factual questions
- Require grounding or explicit uncertainty for claims
- Treat disagreement as a signal to stop and verify
- Persist only validated information; allow everything else to decay

These constraints were portable, testable, and didn’t depend on belief in a system.

## Outcome

The result was not a product or architecture.
It was a way of working that:
- reduced overconfidence
- made failure visible earlier
- kept AI as a tool rather than an authority

Most importantly, it was something I could apply under pressure, without ceremony.

## Takeaway

Good ideas don’t need protection.
Bad ideas do.

The fastest way to improve decision quality—especially when using AI—is to get comfortable deleting your own work before it calcifies.
