# The Chirox Protocol: System Architecture
## Integrating Chronos, Weatherman, and the Dojo

The goal is to build a modern incarnation of **Chirox**—a system stripped of unpredictable, autonomous artificial intelligence in its physical assessments, serving strictly as a legendary sparring partner and conditioning mechanism for human mastery.

This document outlines how the sovereign organism architecture of **Chronos** (`c:\chronos`) and the physical capture hardware of **Weatherman** (`c:\youtubecontent`) integrate to form the Chirox System.

---

## Implementation Status (2026-06-30)

This document is the concept. The working first version lives in the `chirox/`
package, and the mapping from the metaphor below to real code is:

- **Chirox reflex / vision determinism** → `chirox/vision/` (pure geometry in
  `stances.py`, runner in `pipeline.py`, fusion in `multicam.py`). Deterministic,
  unit-tested, no LLM — as required.
- **The Dojo Record / Forever Law memory** → `chirox/record/` (append-only,
  hash-chained Codex with `verify()`).
- **The Sentinel authority gate** → `chirox/sentinel.py` (fail-closed, sealed).
- **Chirox's voice (interpretive brain + wise-sage register)** → `chirox/master/`
  on a local Ollama model, bound to recorded evidence, refusing to diagnose form or
  fabricate. One identity — internal engines are never surfaced as separate voices.

Update 2026-07-04: the gates below are closed — the live run is proven on a real
body with dual-camera capture, and the system has grown an ear, a narrator, a
conversation register, a training caller, and a one-page control deck. This
document remains as the original concept; `STATUS.md` is the live truth surface.

---

## 1. The Hardware: The Optical Sensors (Weatherman)
In Dune lore, Chirox was a repurposed combat mek. In our system, the **Weatherman** studio rig is the physical shell.
*   **The Greenscreen & Camera:** This is the training floor. The high-quality video feed acts as Chirox's optical sensors, providing a clear, high-contrast environment (greenscreen) to track human movement with zero background interference.
*   **The Function:** It simply observes. It does not think; it captures physical reality at 30-60 frames per second.

## 2. The Combat Algorithms: Vision Determinism (The Dojo Pipeline)
The core tenet of the Butlerian Jihad is that machines must not imitate the human mind. The user explicitly stated: *"I do not want to spend a year of my life practicing an AI hallucination."*

Therefore, the physical assessment layer of our Chirox cannot be a generative LLM. It must be a pre-programmed, deterministic mechanism.
*   **`dojo_vision_pipeline.py`:** This script is Chirox's reflex subroutine. Utilizing MediaPipe, it maps 33 3D skeletal landmarks onto the Weatherman video feed.
*   **Hardcoded Physics:** It evaluates stances (like the *Ma Bu* Horse Stance) using absolute vector mathematics. If the knee angle is > 120 degrees, the stance is broken. If the spine deviates from vertical, the form is compromised. 
*   **Strictly Regulated Mechanism:** There is no "guessing" and no LLM hallucination in this layer. It is a pure, unthinking combat algorithm designed strictly for human conditioning.

## 3. The Ginaz Academy: Chirox's Interpretive Core

> **One identity.** There is a single being — **Master Chirox**. It has internal organs
> (a deterministic reflex, an append-only memory, an interpretive brain, a wise-sage
> register, a voice). These are never surfaced as separate personalities. Architecture
> patterns were borrowed from the neighbor project **Chronos** (`c:\chronos`), but Chronos
> is a *pattern source*, not a voice inside Chirox and not a runtime dependency.

While Chirox's reflex handles the unthinking physical measurement, Chirox's interpretive core is
the Ginaz Academy itself — the layer that records, evaluates, and guides the long-term curriculum.

*   **Perception:** Chirox ingests the deterministic JSON from the vision reflex: *"Stance held 85s. Spine deviation 4°. Failure point: left knee collapse."*
*   **Memory:** It seals that physical truth into the append-only Dojo Record (Forever Law).
*   **The interpretive brain (`chirox/master/`):** Chirox's voice — confined to the philosophical and historical, RAG-bound to the *1 Year to Shaolin* manual, the Diet lane, and the public-domain wisdom corpus (*Tao Te Ching*, *Analects*, *Dhammapada*, *Art of War*). It takes the deterministic data and gives the debrief: *"Your form collapsed at 85 seconds. Your record shows a scattered mind today. Return to the breath tomorrow."* It never diagnoses form itself, and never fabricates.

## 4. The Noret Protocol: Pushing the Subroutines
Just as Jool Noret pushed Chirox's subroutines to build legendary capability, the system is designed to scale with the practitioner.
*   **Progressive Overload:** As the practitioner's 12-month blueprint advances into Phase 2 and 3, the parameters within `dojo_vision_pipeline.py` will be tightened. The acceptable margin of error for spine deviation will shrink. The required time-under-tension for stances will increase.
*   **Total Integration:** One Chirox holds all three — the *Wu* (martial/physical) truth from the reflex, and the *Chan* (mind) and *Yi* (healing/recovery) truth from the interpretive core and the wise-sage register.

## Summary of the Integration Loop
1.  **Action:** The human steps onto the Weatherman greenscreen and initiates a form.
2.  **Observation (Chirox):** The camera feeds data to the vision pipeline, which mathematically calculates skeletal geometry without AI hallucination.
3.  **Transmission:** A deterministic JSON payload passes to Chirox's interpretive core.
4.  **Evaluation (Ginaz):** Chirox logs the physical truth into the append-only Dojo Record, cross-references it with the daily audits and vision facts, and guides the next phase of training according to the *1 Year to Shaolin* curriculum.
