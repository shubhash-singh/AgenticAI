import json
from pathlib import Path
from typing import Dict, Any

import os
import re
from dotenv import load_dotenv

from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq


load_dotenv()


# ------------ Utility ------------

def load_spec(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)



def safe_json_parse(text: str) -> Dict[str, Any]:
    stripped = text.strip()

    # strip ```json fences if present
    if stripped.startswith("```"):
        stripped = stripped.strip("`")
        if stripped.startswith("json"):
            stripped = stripped[4:].lstrip()

    # try to extract the first {...} block
    match = re.search(r"\{.*\}", stripped, re.DOTALL)
    if match:
        return json.loads(match.group(0))

    return json.loads(stripped)



# ------------ Step 1: Creation chain ------------

def build_creation_chain():
    llm = ChatGroq(
        model="llama-3.3-70b-versatile",          # strong for code + long-form gen
        temperature=0.7,
        api_key=os.getenv("GROQ_API_KEY_GENERATE_SIMULATION"),
    )

    prompt = ChatPromptTemplate.from_template(
        """
You are an expert educational content designer and front-end developer.

You will receive a JSON object that describes a science/engineering concept.
Your task is to create a SINGLE, SELF-CONTAINED HTML FILE that works well on MOBILE screens.

REQUIREMENTS:
- MOBILE-FIRST, RESPONSIVE DESIGN:
  - Use a single-column layout on small screens.
  - Use fluid widths (e.g., max-width, percentages) and avoid fixed large widths.
  - Ensure no horizontal scrolling on typical phones.
- Use simple, semantic HTML5.
- Use inline <style> for CSS (no external files).
- Use minimal, vanilla JavaScript inside a <script> tag (only if really needed).
- Do NOT include external CDN links (no Tailwind, Bootstrap, etc).
- The tone should be friendly and clear for students.

INTERACTIVITY:
- The "interaction_type" key in the JSON describes how the user interacts:
  - "hover-to-explain": on tap/hover, reveal explanations about parts of the visual or key points.
  - "step-by-step": show steps with a "Next" / "Previous" button.
  - "quiz-like": include a tiny quiz (2–3 questions) with immediate feedback.
- Keep JavaScript simple: toggling visibility, adding/removing CSS classes, updating text.

PAGE STRUCTURE:
- <header> with the title from JSON.
- A short introductory paragraph based on "concept" (simplified if needed).
- A central "visual simulation" section:
  - Use CSS shapes/animations or simple inline SVG to suggest the idea from "visual_focus".
  - Make some part interactive (click, tap, or hover).
- A section that highlights each "key_points" entry with some interactive behavior.
- A short summary/conclusion at the bottom.

IMPORTANT:
- The output MUST be valid HTML, starting with <!DOCTYPE html> and a <html> tag.
- Do NOT include any explanation outside of the HTML (no Markdown, no commentary).
- Do NOT echo the JSON back to the user.

Here is the JSON spec:

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
        bugfix_data = safe_json_parse(bugfix_response.content)

        has_bug = bugfix_data.get("has_bug", False)
        notes = bugfix_data.get("notes", "")
        html = bugfix_data.get("html", html)

        print(f"   - Bugfix notes: {notes}")
        print(f"   - Bugs found and fixed? {has_bug}")

        # Step 3: review phase
        print("▶ Reviewing simulation...")
        review_response = review_chain.invoke({"html": html})
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
