# The Chirox Protocol: System Architecture
## Integrating Chronos, Weatherman, and the Dojo

The goal is to build a modern incarnation of **Chirox**—a system stripped of unpredictable, autonomous artificial intelligence in its physical assessments, serving strictly as a legendary sparring partner and conditioning mechanism for human mastery.

This document outlines how the sovereign organism architecture of **Chronos** (`c:\chronos`) and the physical capture hardware of **Weatherman** (`c:\youtubecontent`) integrate to form the Chirox System.

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

## 3. The Ginaz Academy: The Organism Core (Chronos)
While Chirox handles the unthinking physical collision and measurement, the **Chronos** architecture acts as the Ginaz Academy itself—the overarching structure that records, evaluates, and guides the long-term curriculum.

*   **The Sentinel (Perception Layer):** The Sentinel constantly ingests the JSON payload outputted by the `dojo_vision_pipeline.py`. It receives the hard data: *"Stance held for 85 seconds. Spine deviation 4 degrees. Failure point: Left knee collapse."*
*   **The Director (Routing):** The Director takes this physical data and routes it into the Dojo Record.
*   **Primus (The Core):** Primus acts as the Master, but its domain is strictly confined to the philosophical and the historical. It is heavily RAG-bound to the *1 Year to Shaolin* manual and the foundational texts (*Tao Te Ching*, *The Analects*). Primus takes the deterministic physical data from Chirox and provides the post-session debrief: *"Your physical form collapsed at 85 seconds. Reviewing your emotional audit, your mind was scattered today. Return to the breath tomorrow."*

## 4. The Noret Protocol: Pushing the Subroutines
Just as Jool Noret pushed Chirox's subroutines to build legendary capability, the system is designed to scale with the practitioner.
*   **Progressive Overload:** As the practitioner's 12-month blueprint advances into Phase 2 and 3, the parameters within `dojo_vision_pipeline.py` will be tightened. The acceptable margin of error for spine deviation will shrink. The required time-under-tension for stances will increase.
*   **Total Integration:** The Chirox system provides the *Wu* (martial/physical) truth, while Chronos manages the *Chan* (mind) and *Yi* (healing/recovery) truth. 

## Summary of the Integration Loop
1.  **Action:** The human steps onto the Weatherman greenscreen and initiates a form.
2.  **Observation (Chirox):** The camera feeds data to the vision pipeline, which mathematically calculates skeletal geometry without AI hallucination.
3.  **Transmission:** A deterministic JSON payload is sent to Chronos.
4.  **Evaluation (Ginaz):** Chronos (Primus) logs the physical truth into the Dojo Record, cross-references it with the daily emotional/spiritual audits, and dictates the next phase of training according to the *1 Year to Shaolin* curriculum.
