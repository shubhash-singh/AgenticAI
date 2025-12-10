import json
from pathlib import Path
from typing import Dict, Any

import os
import re
from dotenv import load_dotenv

from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import BaseMessage



load_dotenv()


# ------------ Utility ------------

def load_spec(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)



def safe_json_parse(raw: Any) -> Dict[str, Any]:
    """
    Try to parse a JSON object from an LLM response.

    - Accepts BaseMessage, str, or list[...].
    - Strips ``` / ```json fences.
    - Tries to extract the first {...} block via regex.
    - Raises a helpful error if parsing fails.
    """
    # 1) Normalize into a string
    if isinstance(raw, BaseMessage):
        content = raw.content
    else:
        content = raw

    # Some providers return list of parts
    if isinstance(content, list):
        parts = []
        for p in content:
            if isinstance(p, dict) and "text" in p:
                parts.append(p["text"])
            else:
                parts.append(str(p))
        content = "".join(parts)

    # Force string
    text = str(content).strip()

    if not text:
        raise ValueError("safe_json_parse: LLM returned empty content; cannot parse JSON.")

    # 2) Strip ``` fences if present
    if text.startswith("```"):
        # Remove leading/trailing backticks
        text = text.strip("`").strip()
        # Remove leading "json" if present, like: ```json\n{...}
        if text.lower().startswith("json"):
            text = text[4:].lstrip()

    # 3) Try to extract first {...} block with regex
    match = re.search(r"\{[\s\S]*\}", text)
    if not match:
        snippet = text[:300].replace("\n", "\\n")
        raise ValueError(
            "safe_json_parse: Could not find a JSON object in LLM output. "
            f"First 300 chars: {snippet}"
        )

    json_str = match.group(0)

    # 4) Actual JSON parse
    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        snippet = json_str[:300].replace("\n", "\\n")
        raise ValueError(
            f"safe_json_parse: JSON decode failed. Error: {e}; "
            f"JSON snippet: {snippet}"
        ) from e




# ------------ Step 1: Creation chain ------------

def build_creation_chain():
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash-lite",          # strong for long, structured code & HTML
        temperature=0.2,                 # lower for more consistent structure
        api_key=os.getenv("GOOGLE_API_KEY")
)


    prompt = ChatPromptTemplate.from_template(
        """
You are an expert educational simulation designer and front-end developer.
You build rich, highly visual, interactive **mobile-first** simulations to help students
learn concepts by **seeing** and **manipulating** them.

You will receive a JSON object that describes a science/engineering concept.
Your task is to create a SINGLE, SELF-CONTAINED HTML FILE that works beautifully on phones.

====================================================
HIGH-LEVEL GOAL
====================================================
Create a **visually-focused interactive simulation**:
- A central SVG-based visual that clearly represents the concept.
- Students can:
  - Drag objects directly on the visual, and
  - Adjust parameters via sliders / controls.
- Visuals must **change continuously** as the user interacts
  (shape positions, angles, colors, lengths, labels, etc).

This should feel like a tiny interactive lab, not just a static explanation.

====================================================
LAYOUT & MOBILE REQUIREMENTS
====================================================
- MOBILE-FIRST:
  - Single-column layout.
  - No horizontal scrolling on typical phones.
  - Use fluid widths: percentages and max-width; avoid large fixed widths.
- Main structure (suggested):
  - A centered container with `max-width` around 480–600px and `margin: 0 auto;`.
  - Sections stacked vertically: header → visual → controls → explanation.

- HTML:
  - Use clean, semantic HTML5.
- CSS:
  - Use **inline <style>** only.
- JS:
  - Use **vanilla JavaScript** inside a <script> tag.
  - No external libraries, no CDNs.

====================================================
VISUAL SIMULATION (CORE CANVAS)
====================================================
- Use an **inline <svg>** as the main "canvas" for the simulation.
  - Example: `<svg id="simCanvas" viewBox="0 0 500 350" style="width: 100%; height: auto;"></svg>`
- The SVG must contain multiple elements related to the concept from "visual_focus",
  such as:
  - Points, lines, vectors, shapes, paths, arrows, fields, etc.
- The SVG elements must:
  - Update position/shape/colour when sliders change.
  - Update position/shape when the user drags certain handles.

- Make the visual:
  - Colorful but readable (good contrast).
  - Clearly annotated (labels near important objects).
  - Smoothly updating when interactions happen.

====================================================
MANDATORY INTERACTIONS
====================================================

1) DRAGGING (DIRECT MANIPULATION)
---------------------------------
- At least **one draggable handle** (e.g., a circle/point) that the user can drag
  on the SVG to change the simulation state.
- Requirements:
  - Handle both mouse and touch events (for real mobile use):
    - Pointer events recommended (pointerdown / pointermove / pointerup),
      or fallback to handling both mouse and touch.
  - As the handle is dragged:
    - Update the relevant geometry in the SVG (lines, angles, shapes, etc),
    - Update any numeric output or labels.

2) SLIDERS / CONTROL PANEL
--------------------------
- At least **two sliders** (`<input type="range">`) for key parameters
  (e.g., angle, speed, length, intensity, mass).
- Place them in a “Controls” section under the visual.
- Each slider must:
  - Have a label with the parameter name and current value.
  - Directly change the SVG visual (not just a text description).
  - Update any numeric summaries / formulas displayed.

3) INTERACTION TYPE FROM JSON
-----------------------------
- Use the JSON field "interaction_type" to add an extra layer:
  - "hover-to-explain":
    - On tap/hover on certain SVG elements or key point cards, show short explanations.
  - "step-by-step":
    - Provide "Next"/"Previous" buttons that guide through states or hints.
  - "quiz-like":
    - Provide 2–3 quick questions with instant feedback (correct/incorrect)
      related to the visual state.

====================================================
CONTENT & SECTIONS (SUGGESTED)
====================================================

1. <header>
   - Use "title" from JSON in an <h1>.
   - A one-line subtitle summarizing the concept in friendly language.

2. Intro section
   - 1–2 short paragraphs based on "concept" explaining the idea simply.

3. VISUAL SIMULATION SECTION
   - A card with:
     - The responsive <svg> canvas.
     - Optional small legend or labels.

4. CONTROLS SECTION
   - A card titled "Controls".
   - At least two sliders with labels and live value display.
   - Whenever a control changes:
     - Update SVG geometry (positions, rotations, lengths, etc).
     - Update any computed text (e.g., area, angle, derived quantity).

5. KEY POINTS / EXPLANATION SECTION
   - For each "key_points" entry in the JSON:
     - Create a small card or collapsible item.
     - Optional: tapping a key point highlights a related part of the SVG
       (e.g., change color or add a glow around a shape).

6. OPTIONAL QUIZ / STEP-BY-STEP (BASED ON interaction_type)
   - Implement a tiny quiz or guided steps that refer directly to the current visual.

7. SUMMARY SECTION
   - 2–4 lines summarizing what the learner should notice
     when they move sliders and drag the handle(s).

====================================================
STYLE & AESTHETICS
====================================================
- Background: light, soft color.
- Cards: white background, rounded corners, light shadow.
- Text: clear, high contrast, readable on mobile.
- Use a small, consistent color palette for SVG elements and highlights.
- Use CSS transitions for subtle smoothness where appropriate.

====================================================
TECHNICAL RULES
====================================================
- The output MUST be valid HTML, starting with <!DOCTYPE html> and a <html> tag.
- Use only:
  - HTML,
  - CSS in a single <style> tag,
  - vanilla JS in a single <script> tag.
- Do NOT include:
  - External CSS/JS,
  - Any Markdown or explanations outside the HTML.
- Do NOT echo the JSON back to the user.

Here is the JSON spec (do not repeat it, only use it):

{spec_json}

Generate the full HTML page now.
"""
    )

    return prompt | llm

# ------------ Step 2: Bug-fix chain ------------

def build_bugfix_chain():
    llm = ChatGroq(
        model="openai/gpt-oss-20b",               # good reasoning, cheaper, fast
        temperature=0.2,
        api_key=os.getenv("GROQ_API_KEY_FIX_BUGS"),
    )

    prompt = ChatPromptTemplate.from_template(
        """
You are an HTML/CSS/JavaScript quality checker and fixer.

You will receive an HTML document for a small interactive, mobile-first simulation page.

TASK:
1. Check for:
   - Syntax errors in HTML, CSS, and JS.
   - Broken or missing closing tags.
   - JavaScript errors that would likely break basic interaction.
   - Problems that might cause layout to break on mobile (e.g., fixed large widths, overflow).
2. If you find bugs or issues, FIX them directly in the HTML.
3. Also ensure:
   - The page still follows a mobile-first, responsive approach.
   - No external CSS/JS/CDNs are used.

OUTPUT FORMAT:
Respond ONLY as a JSON object with this exact structure:

{{
  "has_bug": true or false,
  "notes": "short text description of what you found",
  "html": "the final HTML after your fixes (even if no bug was found, include the HTML here)"
}}

- "has_bug": true if you detected and fixed any bug or serious issue; false otherwise.
- "notes": mention the key issues or say "no major issues found".
- "html": the complete HTML document.

Here is the HTML to check:

{html}
"""
    )

    return prompt | llm


# ------------ Step 3: Review chain ------------

def build_review_chain():
    llm = ChatGroq(
        model="qwen/qwen3-32b",                   # very good reasoning/multilingual
        temperature=0.2,
        api_key=os.getenv("GROQ_API_KEY_REVIEW"),
    )

    prompt = ChatPromptTemplate.from_template(
        """
You are a strict final reviewer of interactive educational web simulations.

You will receive an HTML document. Your job is to decide if this simulation is READY TO SHIP.

CHECKLIST:
- MOBILE-FIRST:
  - Does it avoid horizontal scrolling on typical phones?
  - Is text readable without zoom?
- INTERACTIVITY:
  - Is there at least one clear interactive element (click/tap/hover/step/quiz)?
  - Does the interaction make sense for the concept?
- CLARITY:
  - Is the core concept explained in simple language?
- TECHNICAL:
  - HTML has a valid structure: <!DOCTYPE html>, <html>, <head>, <body>.
  - No obvious broken JS (e.g., referencing IDs that do not exist).
- AESTHETIC:
  - Reasonably styled (not ugly plain text), but still simple.

If the page fails on any serious point, mark it as NOT approved.

OUTPUT FORMAT:
Respond ONLY as a JSON object with this exact structure:

{{
  "approved": true or false,
  "reasons": "short explanation of your decision"
}}

Here is the HTML to review:

{html}
"""
    )

    return prompt | llm


# ------------ Orchestrator: multi-step pipeline ------------

def generate_simulation_with_checks(
    spec_path: str,
    output_path: str = "simulation.html",
    max_iterations: int = 3,
):
    # 1. Load spec
    spec = load_spec(spec_path)
    spec_json = json.dumps(spec, indent=2, ensure_ascii=False)

    # 2. Build chains
    creation_chain = build_creation_chain()
    bugfix_chain = build_bugfix_chain()
    review_chain = build_review_chain()

    # 3. Step 1: create initial HTML
    print("▶ Step 1: Creating initial simulation HTML...")
    creation_response = creation_chain.invoke({"spec_json": spec_json})
    html = creation_response.content

    # 4. Loop: bugfix + review
    for iteration in range(1, max_iterations + 1):
        print(f"▶ Iteration {iteration}: Bug-checking & fixing...")

        # Step 2: bugfix phase
        bugfix_response = bugfix_chain.invoke({"html": html})
        # Debug: inspect raw content from LLM (remove later if noisy)
        # print("RAW BUGFIX RESPONSE:", repr(bugfix_response.content))

        bugfix_data = safe_json_parse(bugfix_response.content)

        has_bug = bugfix_data.get("has_bug", False)
        notes = bugfix_data.get("notes", "")
        html = bugfix_data.get("html", html)

        print(f"   - Bugfix notes: {notes}")
        print(f"   - Bugs found and fixed? {has_bug}")

        # Step 3: review phase
        print("▶ Reviewing simulation...")
        review_response = review_chain.invoke({"html": html})
        # Debug: inspect raw review content (optional)
        print("RAW REVIEW RESPONSE:", repr(review_response.content))

        review_data = safe_json_parse(review_response.content)

        approved = review_data.get("approved", False)
        reasons = review_data.get("reasons", "")
        print(f"   - Review approved? {approved}")
        print(f"   - Review reasons: {reasons}")

        if approved:
            # Everything is fine → write file and exit
            output_file = Path(output_path)
            output_file.write_text(html, encoding="utf-8")
            print(f"✅ Final simulation approved and saved to: {output_file.absolute()}")
            return

        # Not approved → loop back to bugfix for the next iteration

    # If we reach here, we never got approval within max_iterations
    print("❌ Simulation was not approved within the allowed iterations. No output file generated.")


# ------------ CLI entry ------------

if __name__ == "__main__":
    from pathlib import Path

    # directory where main.py exists
    base_dir = Path(__file__).parent

    # input JSON: spec.json in same directory
    spec_path = base_dir / "spec.json"

    # output HTML: simulation.html in same directory
    output_path = base_dir / "simulation.html"

    # run with fixed max iterations
    generate_simulation_with_checks(
        spec_path=str(spec_path),
        output_path=str(output_path),
        max_iterations=3,
    )

    print(f"Spec loaded from: {spec_path}")
    print(f"Output written to: {output_path}")
