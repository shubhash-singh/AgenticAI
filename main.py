import json
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

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
    Enhanced with better error handling and extraction.
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
        text = text.strip("`").strip()
        if text.lower().startswith("json"):
            text = text[4:].lstrip()

    # 3) Try to extract first {...} block with regex (greedy to get full object)
    # Changed from non-greedy to handle nested objects better
    match = re.search(r'\{(?:[^{}]|(?:\{[^{}]*\}))*\}', text, re.DOTALL)
    if not match:
        # Fallback: try to find content between first { and last }
        first_brace = text.find('{')
        last_brace = text.rfind('}')
        if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
            json_str = text[first_brace:last_brace + 1]
        else:
            snippet = text[:300].replace("\n", "\\n")
            raise ValueError(
                "safe_json_parse: Could not find a JSON object in LLM output. "
                f"First 300 chars: {snippet}"
            )
    else:
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


def check_minimum_requirements(html: str) -> List[str]:
    """
    Enhanced sanity checks with more comprehensive validation.
    """
    issues = []

    # Check for main SVG canvas
    if 'id="simCanvas"' not in html and "id='simCanvas'" not in html:
        issues.append("Missing main SVG element with id='simCanvas'.")

    # Check for sliders
    range_count = html.count('<input type="range"')
    if range_count < 2:
        issues.append(f"Expected at least 2 sliders (<input type='range'>), found {range_count}.")

    # Check for interaction handlers
    has_interaction = any(handler in html for handler in [
        "pointerdown", "mousedown", "touchstart", "onclick"
    ])
    if not has_interaction:
        issues.append("No interaction handlers found; interactive elements may be missing.")

    # Check for core functions
    if "updateSimulation" not in html:
        issues.append("Missing updateSimulation() function.")
    
    if "initSimulation" not in html:
        issues.append("Missing initSimulation() function.")

    # Check for DOMContentLoaded
    if "DOMContentLoaded" not in html:
        issues.append("Missing DOMContentLoaded initialization.")
    
    # Check for basic HTML structure
    if "<!DOCTYPE html>" not in html:
        issues.append("Missing DOCTYPE declaration.")
    
    # Check for viewport meta tag (mobile-first requirement)
    if '<meta name="viewport"' not in html:
        issues.append("Missing viewport meta tag for mobile responsiveness.")

    return issues


# ------------ Step 1: Planner chain (OPTIMIZED) ------------

def build_planner_chain():
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash-lite",
        temperature=0.2,
        api_key=os.getenv("GOOGLE_API_KEY_PLANNING")
    )

    # IMPROVED: More structured and concise prompt
    prompt = ChatPromptTemplate.from_template(
        """You are an expert instructional designer planning an interactive physics/science simulation.

Analyze this specification and create a structured design plan:

{spec_json}

Provide a clear, actionable plan using EXACTLY this format:

# Visual Concept
[2-3 sentences describing the core visual representation]

# Draggable Elements
1. [Name]: [Location in SVG], controls [what parameter]
2. [Name]: [Location in SVG], controls [what parameter]

# Sliders (exactly 2)
1. [Name]: min=[X], max=[Y], default=[Z], controls [parameter description]
2. [Name]: min=[X], max=[Y], default=[Z], controls [parameter description]

# State Variables
- [variable1]: [description]
- [variable2]: [description]
- [variable3]: [description]

# Visual Changes on Interaction
- When [parameter] changes: [specific SVG changes]
- When [parameter] changes: [specific SVG changes]

# Interaction Flow
1. [Step describing user action and result]
2. [Step describing user action and result]
3. [Step describing user action and result]

# Quiz Questions
1. Q: [Question]
   A: [Correct answer]
   Explanation: [Why this is correct]
2. Q: [Question]
   A: [Correct answer]
   Explanation: [Why this is correct]

Keep responses concrete and actionable. Focus on what will be implemented, not why."""
    )

    return prompt | llm


# ------------ Step 2: Creation chain (OPTIMIZED) ------------

def build_creation_chain():
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash-lite",
        temperature=0.2,
        api_key=os.getenv("GOOGLE_API_KEY_BUILDING"),
    )

    # IMPROVED: Streamlined prompt with clearer structure and requirements
    prompt = ChatPromptTemplate.from_template(
"""You are an expert at building interactive educational simulations. Create a complete, working HTML file.

=== CORE REQUIREMENTS ===

1. STRUCTURE (MANDATORY):
   - Single HTML file with inline <style> and <script>
   - Mobile-first: max-width 600px, responsive, no horizontal scroll
   - Clean sections: header → visual → controls → explanation → quiz

2. INTERACTIVITY (MANDATORY):
   - SVG with id="simCanvas" (viewBox="0 0 500 350")
   - Minimum 2 sliders with <input type="range">
   - At least 1 draggable handle in SVG
   - All changes must call updateSimulation()

3. JAVASCRIPT PATTERN (REQUIRED):
   Create these two main functions:
   - initSimulation(): Gets DOM elements, sets up event listeners, calls updateSimulation()
   - updateSimulation(): Reads current state, updates SVG geometry and text displays
   
   Initialize with: document.addEventListener("DOMContentLoaded", initSimulation);

4. VISUAL REQUIREMENTS:
   - Clean, modern design with good contrast
   - Readable labels and values
   - Smooth visual updates on interaction
   - Color-coded elements for clarity

5. INTERACTION TYPE (from spec):
   - "hover-to-explain": Add clickable info icons
   - "step-by-step": Add next/prev buttons with guidance
   - "quiz-like": Add 2-3 quiz questions with instant feedback

=== YOUR DESIGN PLAN (FOLLOW CLOSELY) ===
{plan}

=== ORIGINAL SPECIFICATION (REFERENCE) ===
{spec_json}

=== OUTPUT ===
Generate ONLY the complete HTML code. Start with <!DOCTYPE html>.
No explanations, no markdown, just working HTML."""
    )

    return prompt | llm


# ------------ Step 3: Bug-fix chain (OPTIMIZED) ------------

def build_bugfix_chain():
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash-lite",
        temperature=0.2,  # Reduced from 0.3 for more consistent fixes
        api_key=os.getenv("GOOGLE_API_KEY_BUGFIX"),
    )

    # IMPROVED: More focused on critical bugs
    prompt = ChatPromptTemplate.from_template(
        """You are a code quality checker. Review this HTML and fix ONLY critical issues.

FOCUS ON:
1. Syntax errors (unclosed tags, missing quotes, invalid JavaScript)
2. Broken functionality (missing IDs, undefined variables, broken event handlers)
3. Mobile layout breaking issues (fixed widths > screen, overflow problems)
4. Missing viewport meta tag

DO NOT:
- Rewrite working code
- Change design/styling unless broken
- Remove or rename IDs
- Add new features

RESPOND ONLY with this JSON format:
{{
  "has_bug": true/false,
  "notes": "Brief description of fixes made",
  "html": "Complete fixed HTML"
}}

HTML to review:
{html}"""
    )

    return prompt | llm


# ------------ Step 4: Student Feedback chain (OPTIMIZED) ------------

def build_student_feedback_chain():
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash-lite",
        temperature=0.6,  # Reduced from 0.7 for more focused feedback
        api_key=os.getenv("GOOGLE_API_KEY_BUGFIX")
    )

    # IMPROVED: More specific evaluation criteria
    prompt = ChatPromptTemplate.from_template(
        """You are a high school student testing this simulation. Be specific and constructive.

Evaluate:
- Is it immediately clear what to do?
- Are the controls labeled and easy to find?
- Do you understand what's happening when you interact?
- Are there any confusing or broken parts?
- What would make this better?

RESPOND ONLY with this exact JSON structure:
{{
  "first_impressions": ["point 1", "point 2"],
  "visual": ["point 1", "point 2"],
  "controls": ["point 1", "point 2"],
  "explanations": ["point 1", "point 2"],
  "bugs_or_issues": ["point 1" or "None found"],
  "suggestions": ["point 1", "point 2"]
}}

Keep each point SHORT (1 sentence). Be specific, not generic.

HTML:
{html}"""
    )

    return prompt | llm


# ------------ Step 5: Incorporate Feedback chain (OPTIMIZED) ------------

def build_incorporate_feedback_chain():
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash-lite",
        temperature=0.2,
        api_key=os.getenv("GOOGLE_API_KEY_BUGFIX")
    )

    # IMPROVED: Clearer constraints on what to change
    prompt = ChatPromptTemplate.from_template(
        """Update this HTML based on student feedback. Make MINIMAL, targeted improvements.

ALLOWED CHANGES:
✓ Improve labels and instructions
✓ Add helpful tooltips or hints
✓ Adjust colors for better readability
✓ Fix confusing UI elements
✓ Add brief explanatory text

FORBIDDEN CHANGES:
✗ Don't rewrite the layout
✗ Don't remove id="simCanvas"
✗ Don't remove sliders or draggable elements
✗ Don't change core functionality
✗ Don't add external libraries

Student Feedback:
{feedback_json}

Current HTML:
{html}

Return ONLY the updated HTML. No explanations."""
    )

    return prompt | llm


# ------------ Step 6: Review chain (OPTIMIZED) ------------

def build_review_chain():
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash-lite",
        temperature=0.1,  # Reduced from 0.2 for more consistent reviews
        api_key=os.getenv("GOOGLE_API_KEY_BUGFIX")
    )

    # IMPROVED: Clearer pass/fail criteria
    prompt = ChatPromptTemplate.from_template(
        """You are the final quality gate. Decide if this simulation is READY TO SHIP.

MUST HAVE (or REJECT):
✓ Valid HTML structure (DOCTYPE, head, body)
✓ Viewport meta tag for mobile
✓ Working SVG with id="simCanvas"
✓ At least 2 functioning sliders
✓ At least 1 interactive element (drag or click)
✓ updateSimulation() and initSimulation() functions
✓ DOMContentLoaded event listener
✓ Clear concept explanation

SHOULD HAVE (nice but not blocking):
- Good visual design
- Helpful labels
- Quiz or step-by-step interaction

RESPOND ONLY with this JSON:
{{
  "approved": true/false,
  "reasons": "Specific reason for approval/rejection"
}}

Be strict but fair. Only approve if it will work for students.

HTML:
{html}"""
    )

    return prompt | llm


# ------------ Orchestrator: multi-step pipeline (OPTIMIZED) ------------

def generate_simulation_with_checks(
    spec_path: str,
    output_path: str = "simulation.html",
    max_iterations: int = 1,
    save_intermediates: bool = True,
) -> Tuple[bool, str]:
    """
    Generate simulation with improved flow and error handling.
    
    Returns:
        Tuple of (success: bool, final_html: str)
    """
    print("=" * 60)
    print("SIMULATION GENERATION PIPELINE")
    print("=" * 60)
    
    # 1. Load spec
    print("\n[1/7] Loading specification...")
    try:
        spec = load_spec(spec_path)
        spec_json = json.dumps(spec, indent=2, ensure_ascii=False)
        print(f"✓ Loaded spec: {spec.get('title', 'Untitled')}")
    except Exception as e:
        print(f"✗ Failed to load spec: {e}")
        return False, ""

    # 2. Build chains once (efficiency improvement)
    print("\n[2/7] Initializing AI chains...")
    try:
        planner_chain = build_planner_chain()
        creation_chain = build_creation_chain()
        bugfix_chain = build_bugfix_chain()
        student_feedback_chain = build_student_feedback_chain()
        incorporate_feedback_chain = build_incorporate_feedback_chain()
        review_chain = build_review_chain()
        print("✓ All chains initialized")
    except Exception as e:
        print(f"✗ Failed to initialize chains: {e}")
        return False, ""

    # 3. Planning phase
    print("\n[3/7] Planning simulation design...")
    try:
        plan_message = planner_chain.invoke({"spec_json": spec_json})
        plan = plan_message.content
        
        if save_intermediates:
            Path("plan_output.md").write_text(plan, encoding="utf-8")
        
        print("✓ Plan generated")
        print(f"   Preview: {plan[:150]}...")
    except Exception as e:
        print(f"✗ Planning failed: {e}")
        return False, ""

    # 4. Creation phase
    print("\n[4/7] Creating initial simulation...")
    try:
        creation_response = creation_chain.invoke({
            "spec_json": spec_json, 
            "plan": plan
        })
        html = creation_response.content

        if save_intermediates:
            Path("creation_output.html").write_text(html, encoding="utf-8")

        # Quick validation
        issues = check_minimum_requirements(html)
        if issues:
            print("⚠ Initial validation issues:")
            for issue in issues:
                print(f"   - {issue}")
        else:
            print("✓ Initial creation passed validation")
            
    except Exception as e:
        print(f"✗ Creation failed: {e}")
        return False, ""

    # 5. First bug-fix pass
    print("\n[5/7] First bug-fix pass...")
    try:
        bugfix_response = bugfix_chain.invoke({"html": html})
        bugfix_data = safe_json_parse(bugfix_response.content)
        html = bugfix_data.get("html", html)
        
        if bugfix_data.get("has_bug", False):
            print(f"✓ Fixed bugs: {bugfix_data.get('notes', 'Various fixes')}")
        else:
            print("✓ No critical bugs found")
            
        if save_intermediates:
            Path("bugfix_output.html").write_text(html, encoding="utf-8")
            
    except Exception as e:
        print(f"⚠ Bug-fix encountered error (continuing): {e}")

    # 6. Student feedback phase
    print("\n[6/7] Gathering student feedback...")
    try:
        feedback_response = student_feedback_chain.invoke({"html": html})
        feedback_data = safe_json_parse(feedback_response.content)
        feedback_json_str = json.dumps(feedback_data, indent=2, ensure_ascii=False)

        if save_intermediates:
            Path("student_feedback.json").write_text(feedback_json_str, encoding="utf-8")
        
        # Show summary
        suggestions = feedback_data.get("suggestions", [])
        issues = feedback_data.get("bugs_or_issues", [])
        print(f"✓ Feedback received: {len(suggestions)} suggestions, {len(issues)} issues")
        
    except Exception as e:
        print(f"⚠ Feedback gathering failed (skipping): {e}")
        feedback_json_str = "{}"

    # 7. Incorporate feedback
    print("\n[7/7] Incorporating feedback and final polish...")
    try:
        # Only incorporate if we have meaningful feedback
        if feedback_json_str != "{}":
            incorporate_response = incorporate_feedback_chain.invoke({
                "html": html,
                "feedback_json": feedback_json_str,
            })
            html = incorporate_response.content
            print("✓ Feedback incorporated")
        else:
            print("⊘ Skipping feedback incorporation (no feedback)")

        if save_intermediates:
            Path("feedback_incorporated_output.html").write_text(html, encoding="utf-8")

        # Second bug-fix pass
        print("  Running final bug-fix...")
        bugfix_response_2 = bugfix_chain.invoke({"html": html})
        bugfix_data_2 = safe_json_parse(bugfix_response_2.content)
        html = bugfix_data_2.get("html", html)
        
        if bugfix_data_2.get("has_bug", False):
            print(f"  ✓ Final fixes: {bugfix_data_2.get('notes', 'Various fixes')}")
        
    except Exception as e:
        print(f"⚠ Feedback incorporation encountered error (continuing): {e}")

    # 8. Final review
    print("\n" + "=" * 60)
    print("FINAL REVIEW")
    print("=" * 60)
    try:
        review_response = review_chain.invoke({"html": html})
        review_data = safe_json_parse(review_response.content)

        approved = review_data.get("approved", False)
        reasons = review_data.get("reasons", "")
        
        print(f"\nStatus: {'✅ APPROVED' if approved else '❌ NOT APPROVED'}")
        print(f"Reason: {reasons}")
        
    except Exception as e:
        print(f"⚠ Review failed: {e}")
        approved = False
        reasons = "Review process encountered an error"

    # 9. Save final output
    output_file = Path(output_path)
    output_file.write_text(html, encoding="utf-8")
    
    if save_intermediates:
        Path("review_output.html").write_text(html, encoding="utf-8")

    # Final validation
    final_issues = check_minimum_requirements(html)
    
    print("\n" + "=" * 60)
    print("PIPELINE COMPLETE")
    print("=" * 60)
    print(f"Output saved to: {output_file.absolute()}")
    
    if final_issues:
        print(f"\n⚠ Final validation found {len(final_issues)} issues:")
        for issue in final_issues:
            print(f"   - {issue}")
    else:
        print("\n✓ Final validation passed all checks")
    
    return approved, html


# ------------ CLI entry ------------

if __name__ == "__main__":
    base_dir = Path(__file__).parent
    spec_path = base_dir / "spec.json"
    output_path = base_dir / "simulation.html"

    success, html = generate_simulation_with_checks(
        spec_path=str(spec_path),
        output_path=str(output_path),
        max_iterations=1,
        save_intermediates=True,
    )

    print(f"\n{'=' * 60}")
    if success:
        print("✅ Simulation successfully generated and approved!")
    else:
        print("⚠ Simulation generated but may need manual review.")
    print(f"{'=' * 60}\n")