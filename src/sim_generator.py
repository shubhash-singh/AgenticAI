# sim_generator.py
"""
Simulation generation logic and orchestration.

Saves all node outputs into a timestamped directory under `output/`:
  output/YYYY-MM-DD_HH-MM-SS/

This module expects chain-like objects with an `invoke(kwargs: dict)` method
that returns an object having `.content` (same shape as your original script).
"""

import json
from pathlib import Path
from typing import Dict, Any, List, Tuple
import re
from datetime import datetime


# ---------- Utilities ----------

def load_spec(path: str) -> Dict[str, Any]:
    """Load spec JSON - expects single concept format"""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def safe_json_parse(raw: Any) -> Dict[str, Any]:
    """Try to parse a JSON object from an LLM response."""
    if hasattr(raw, "content"):
        content = raw.content
    else:
        content = raw

    if isinstance(content, list):
        parts = []
        for p in content:
            if isinstance(p, dict) and "text" in p:
                parts.append(p["text"])
            else:
                parts.append(str(p))
        content = "".join(parts)

    text = str(content).strip()

    if not text:
        raise ValueError("safe_json_parse: LLM returned empty content.")

    # Remove markdown code blocks if present
    if text.startswith("```"):
        text = text.strip("`").strip()
        if text.lower().startswith("json"):
            text = text[4:].lstrip()
        elif text.lower().startswith("html"):
            text = text[4:].lstrip()

    # If the model returned raw HTML (common when it ignores the JSON wrapper), wrap it
    stripped_lower = text.lstrip().lower()
    if stripped_lower.startswith("<!doctype") or stripped_lower.startswith("<html"):
        return {"index.html": text}

    # Try to find JSON object
    match = re.search(r'\{(?:[^{}]|(?:\{[^{}]*\}))*\}', text, re.DOTALL)
    if not match:
        first_brace = text.find('{')
        last_brace = text.rfind('}')
        if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
            json_str = text[first_brace:last_brace + 1]
        else:
            # As last resort, if it looks like HTML, wrap it
            if "<html" in text.lower() or "<!doctype" in text.lower():
                return {"index.html": text}
            snippet = text[:300].replace("\n", "\\n")
            raise ValueError(
                f"safe_json_parse: Could not find JSON. First 300 chars: {snippet}"
            )
    else:
        json_str = match.group(0)

    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        # Fallback: if the extracted snippet still looks like HTML, wrap it.
        lower = json_str.lower()
        if "<html" in lower or "<!doctype" in lower or "<style" in lower:
            return {"index.html": json_str}
        snippet = json_str[:300].replace("\n", "\\n")
        raise ValueError(
            f"safe_json_parse: JSON decode failed. Error: {e}; snippet: {snippet}"
        ) from e


def extract_html_from_response(response_content: str) -> str:
    """
    Extract pure HTML from LLM response, handling various formats:
    - JSON wrapped: {"index.html": "..."}
    - Markdown wrapped: ```html ... ```
    - Raw HTML
    """
    text = str(response_content).strip()
    
    # Remove markdown code blocks
    if text.startswith("```"):
        text = text.strip("`").strip()
        if text.lower().startswith("json"):
            text = text[4:].lstrip()
        elif text.lower().startswith("html"):
            text = text[4:].lstrip()
    
    # If it's already HTML, return it
    if text.lstrip().lower().startswith("<!doctype") or text.lstrip().lower().startswith("<html"):
        return text
    
    # Try to parse as JSON and extract index.html
    try:
        data = json.loads(text)
        if isinstance(data, dict) and "index.html" in data:
            return data["index.html"]
    except json.JSONDecodeError:
        pass
    
    # Try to find HTML within the text
    lower = text.lower()
    
    # Look for <!doctype or <html
    doctype_start = lower.find("<!doctype")
    html_start = lower.find("<html")
    
    start_pos = -1
    if doctype_start != -1:
        start_pos = doctype_start
    elif html_start != -1:
        start_pos = html_start
    
    if start_pos != -1:
        # Find the closing </html>
        end_pos = lower.rfind("</html>")
        if end_pos != -1:
            return text[start_pos:end_pos + len("</html>")]
        else:
            # No closing tag found, return from start to end
            return text[start_pos:]
    
    # If nothing worked, return the original text
    return text


def check_minimum_requirements(html: str) -> List[str]:
    """Check single-file HTML requirements."""
    issues = []

    if "<!DOCTYPE html>" not in html and "<!doctype html>" not in html:
        issues.append("Missing DOCTYPE declaration.")
    
    if '<meta name="viewport"' not in html:
        issues.append("Missing viewport meta tag for mobile.")

    # Check for basic interactive elements
    has_controls = any(control in html for control in [
        '<input', '<button', '<select', 'onclick', 'addEventListener'
    ])
    if not has_controls:
        issues.append("No interactive controls found.")

    # Check for inline styles or minimal styling
    if '<style>' not in html and 'style=' not in html:
        issues.append("No styling found (inline or embedded).")

    return issues


def enforce_minimum_requirements(html: str) -> str:
    """
    Add minimal fixes if basic requirements are missing.
    Ensures viewport meta tag and DOCTYPE exist.
    """
    lower = html.lower()
    
    # Add viewport if missing
    if '<meta name="viewport"' not in lower:
        insert = '<meta name="viewport" content="width=device-width, initial-scale=1.0">'
        if "<head>" in lower:
            html = html.replace("<head>", f"<head>\n    {insert}", 1)
        elif "<HEAD>" in html:
            html = html.replace("<HEAD>", f"<HEAD>\n    {insert}", 1)
        else:
            # Add a head section
            if "<html>" in lower:
                html = html.replace("<html>", f"<html>\n<head>\n    {insert}\n</head>", 1)
            elif "<HTML>" in html:
                html = html.replace("<HTML>", f"<HTML>\n<head>\n    {insert}\n</head>", 1)
    
    # Add DOCTYPE if missing
    if "<!doctype" not in lower:
        html = "<!DOCTYPE html>\n" + html
    
    return html


def generate_default_blueprint_from_spec(spec: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build a reasonable CBSE Class 7 blueprint from the spec.json when planner LLM fails.
    Uses values from spec where possible and makes safe assumptions.
    """
    concept = spec.get("Concept", "Unknown Concept")
    short_desc = spec.get("Description", f"A simple simulation about {concept}.")
    
    # sensible default variables for many physical science topics
    default_vars = [
        {"name": "Intensity", "min": 0, "max": 100, "default": 50, "unit": "%"},
        {"name": "Time", "min": 1, "max": 60, "default": 10, "unit": "s"}
    ]

    # If spec suggests heat/temperature, prefer temperature variable
    topic_lower = str(concept).lower()
    if "heat" in topic_lower or "temperature" in topic_lower:
        default_vars = [
            {"name": "Temperature", "min": 0, "max": 100, "default": 25, "unit": "°C"},
            {"name": "Material", "min": 1, "max": 3, "default": 1, "unit": "choice"}
        ]

    blueprint = {
        "learning_objectives": [
            f"Understand what {concept} means.",
            "See how changing one variable affects the outcome.",
            "Learn to record simple observations."
        ],
        "key_concepts": [
            concept,
            "cause and effect",
            "variables and observation"
        ],
        "variables_to_simulate": default_vars[:2],
        "user_interactions": {
            "sliders": [f"Slider to set {v['name']}" for v in default_vars[:2]],
            "buttons": ["Start simulation", "Reset to defaults"],
            "other": "Tap to pause or touch-drag small objects"
        },
        "simulation_logic": [
            "Step 1: Read current values of controls.",
            "Step 2: Update the visual area to reflect the new values.",
            "Step 3: If Start pressed, animate changes over time."
        ],
        "mobile_ui_plan": {
            "layout": "vertical single column",
            "sections": ["Header", "Instructions", "Simulation area", "Controls", "Questions"],
            "touch_targets": "minimum 44px"
        },
        "misconceptions_to_address": [
            "More of something always means faster change (not always true).",
            "If two materials look the same they behave the same (not always true)."
        ],
        "text_instructions_for_students": str(short_desc)[:200] + " Use the sliders and Start button to explore.",
        "file_target": "single_file_html",
        "safety_constraints": ["No real heat sources shown; keep examples conceptual."]
    }
    return blueprint


# ---------- Output helpers ----------

def make_timestamped_output_dir(base_dir: str = "output") -> Path:
    """
    Create a directory like:
      output/YYYY-MM-DD_HH-MM-SS/
    Returns the Path to the timestamped folder.
    """
    now = datetime.now()
    folder_name = now.strftime("%Y-%m-%d_%H-%M-%S")
    root = Path(base_dir) / folder_name
    root.mkdir(parents=True, exist_ok=True)
    return root


# ---------- Orchestrator ----------

def generate_simulation_with_checks(
    spec_path: str,
    planner_chain,
    creation_chain,
    bugfix_chain,
    student_interaction_chain,
    incorporate_feedback_chain,
    review_chain,
    save_intermediates: bool = True,
    output_root: str = "output",
) -> Tuple[bool, str, Path]:
    """
    Orchestrate generation using provided chain-like objects.

    All outputs are written to:
      output_root/YYYY-MM-DD_HH-MM-SS/

    Returns (passed: bool, html_text: str, output_folder: Path)
    """
    print("=" * 70)
    print("SIMULATION GENERATOR")
    print("=" * 70)
    
    # prepare output folder - always create it
    output_dir = make_timestamped_output_dir(output_root)
    print(f"Outputs will be saved to: {output_dir}")

    # 1. Load spec
    print("\n[1/7] Loading concept...")
    try:
        spec = load_spec(spec_path)
        spec_json = json.dumps(spec, indent=2, ensure_ascii=False)
        concept_name = spec.get('Concept', 'Unknown Concept')
        print(f"✓ Concept: {concept_name}")
        if save_intermediates:
            (output_dir / "spec.json").write_text(spec_json, encoding="utf-8")
    except Exception as e:
        print(f"✗ Failed to load: {e}")
        return False, "", output_dir

    # 2. Chains presence check
    print("\n[2/7] Validating provided agents...")
    try:
        for name, c in [
            ("planner_chain", planner_chain),
            ("creation_chain", creation_chain),
            ("bugfix_chain", bugfix_chain),
            ("student_interaction_chain", student_interaction_chain),
            ("incorporate_feedback_chain", incorporate_feedback_chain),
            ("review_chain", review_chain),
        ]:
            if not hasattr(c, "invoke"):
                raise ValueError(f"{name} has no 'invoke' method.")
        print("✓ All agent objects look callable (have invoke)")
    except Exception as e:
        print(f"✗ Agent validation failed: {e}")
        return False, "", output_dir

    # 3. PLANNER NODE
    print("\n[3/7] Planning simulation (Planner Agent)...")
    try:
        plan_response = planner_chain.invoke({"spec_json": spec_json})
        raw_plan_content = getattr(plan_response, "content", str(plan_response))

        # Save raw planner response
        if save_intermediates:
            (output_dir / "1_planner_raw_response.txt").write_text(
                str(raw_plan_content), encoding="utf-8"
            )

        parsed = False
        try:
            plan_data = safe_json_parse(raw_plan_content)
            parsed = True
            plan_json = json.dumps(plan_data, indent=2, ensure_ascii=False)
            if save_intermediates:
                (output_dir / "1_planner_blueprint.json").write_text(plan_json, encoding="utf-8")
            print("✓ Blueprint created")
            print(f"   Objectives: {len(plan_data.get('learning_objectives', []))}")
            print(f"   Variables: {len(plan_data.get('variables_to_simulate', []))}")
        except Exception as e_parse:
            print(f"⚠ Planner parse failed: {e_parse}; attempting retry...")
            if save_intermediates:
                (output_dir / "1_planner_parse_error.txt").write_text(str(e_parse), encoding="utf-8")
            try:
                retry_resp = planner_chain.invoke({"spec_json": spec_json})
                raw_retry = getattr(retry_resp, "content", str(retry_resp))
                if save_intermediates:
                    (output_dir / "1_planner_retry_raw_response.txt").write_text(str(raw_retry), encoding="utf-8")
                plan_data = safe_json_parse(raw_retry)
                parsed = True
                plan_json = json.dumps(plan_data, indent=2, ensure_ascii=False)
                if save_intermediates:
                    (output_dir / "1_planner_blueprint.json").write_text(plan_json, encoding="utf-8")
                print("✓ Blueprint created (after retry)")
            except Exception as e_retry:
                print(f"⚠ Using fallback blueprint: {e_retry}")
                if save_intermediates:
                    (output_dir / "1_planner_final_error.txt").write_text(str(e_retry), encoding="utf-8")
                try:
                    plan_data = generate_default_blueprint_from_spec(spec)
                    plan_json = json.dumps(plan_data, indent=2, ensure_ascii=False)
                    if save_intermediates:
                        (output_dir / "1_planner_blueprint_fallback.json").write_text(plan_json, encoding="utf-8")
                    print("✓ Fallback blueprint generated")
                    parsed = True
                except Exception as e_fb:
                    print(f"✗ Fallback generation failed: {e_fb}")
                    return False, "", output_dir
        
        if not parsed:
            print("✗ Planning failed")
            return False, "", output_dir
    except Exception as e:
        print(f"✗ Planning invocation failed: {e}")
        return False, "", output_dir

    # 4. CREATOR NODE
    print("\n[4/7] Creating index.html (Creator Agent)...")
    try:
        creation_response = creation_chain.invoke({
            "spec_json": spec_json, 
            "plan": plan_json
        })
        
        raw_content = getattr(creation_response, "content", str(creation_response))
        
        # Save raw response for debugging
        if save_intermediates:
            (output_dir / "2_creator_raw_response.txt").write_text(str(raw_content), encoding="utf-8")
        
        # Extract HTML from response
        html = extract_html_from_response(raw_content)
        
        # Save the extracted HTML
        if save_intermediates:
            (output_dir / "2_creator_output.html").write_text(html, encoding="utf-8")

        issues = check_minimum_requirements(html)
        if issues:
            print("⚠ Initial issues:")
            for issue in issues:
                print(f"   - {issue}")
        else:
            print("✓ Basic validation passed")
            
    except Exception as e:
        print(f"✗ Creation failed: {e}")
        if save_intermediates:
            (output_dir / "2_creator_error.txt").write_text(str(e), encoding="utf-8")
        return False, "", output_dir

    # 5. BUGFIX NODE
    print("\n[5/7] Fixing issues (Bugfix Agent)...")
    try:
        bugfix_response = bugfix_chain.invoke({"html": html})
        raw_bugfix = getattr(bugfix_response, "content", str(bugfix_response))
        
        # Save raw bugfix response
        if save_intermediates:
            (output_dir / "3_bugfix_raw_response.txt").write_text(str(raw_bugfix), encoding="utf-8")
        
        try:
            bugfix_data = safe_json_parse(raw_bugfix)
            if "index.html" in bugfix_data:
                html = bugfix_data["index.html"]
            explanations = bugfix_data.get("explanations", [])
            if explanations:
                print(f"✓ Fixed {len(explanations)} issues:")
                for exp in explanations[:3]:
                    print(f"   - {exp}")
        except Exception as e_parse:
            print(f"⚠ Bugfix parse failed, extracting HTML: {e_parse}")
            html = extract_html_from_response(raw_bugfix)
        
        # Enforce minimum requirements
        html = enforce_minimum_requirements(html)
        
        if save_intermediates:
            (output_dir / "3_bugfix_output.html").write_text(html, encoding="utf-8")
        
        print("✓ Bugfix complete")
            
    except Exception as e:
        print(f"⚠ Bugfix error: {e}")
        if save_intermediates:
            (output_dir / "3_bugfix_error.txt").write_text(str(e), encoding="utf-8")

    # 6. STUDENT INTERACTION NODE  
    print("\n[6/7] Generating student questions (Student Interaction Agent)...")
    try:
        interaction_response = student_interaction_chain.invoke({
            "spec_json": spec_json,
            "plan": plan_json
        })
        interaction_data = safe_json_parse(interaction_response.content)
        
        if save_intermediates:
            (output_dir / "4_student_interaction.json").write_text(
                json.dumps(interaction_data, indent=2), 
                encoding="utf-8"
            )
        
        print(f"✓ Generated {len(interaction_data.get('questions', []))} questions")
        
    except Exception as e:
        print(f"⚠ Interaction generation error: {e}")
        if save_intermediates:
            (output_dir / "4_interaction_error.txt").write_text(str(e), encoding="utf-8")

    # 7. REVIEW NODE
    print("\n[7/7] REVIEW (Review Agent)")
    try:
        review_response = review_chain.invoke({"html": html})
        review_data = safe_json_parse(review_response.content)

        if save_intermediates:
            (output_dir / "6_review_results.json").write_text(
                json.dumps(review_data, indent=2), encoding="utf-8"
            )

        scores = review_data.get("scores", {})
        passed = review_data.get("pass", False)
        required_changes = review_data.get("required_changes", [])
        
        print(f"\nScores:")
        for criterion, score in scores.items():
            status = "✓" if score >= 3 else "✗"
            print(f"  {status} {criterion}: {score}/5")
        
        avg_score = sum(scores.values()) / len(scores) if scores else 0
        print(f"\nAverage Score: {avg_score:.2f}/5.0")
        print(f"Status: {'✅ APPROVED' if passed else '❌ NEEDS REVISION'}")
        
        if not passed and required_changes:
            print("Required changes:")
            for change in required_changes[:5]:
                print(f"  - {change}")
        
    except Exception as e:
        print(f"⚠ Review failed: {e}")
        if save_intermediates:
            (output_dir / "6_review_error.txt").write_text(str(e), encoding="utf-8")
        passed = False

    # Save final output - ensure it's clean HTML
    final_html = enforce_minimum_requirements(html)
    (output_dir / "5_final_output.html").write_text(final_html, encoding="utf-8")
    
    print("\n" + "=" * 70)
    print("GENERATION COMPLETE")
    print("=" * 70)
    print(f"All outputs saved to: {output_dir}")
    print(f"Primary output file: {output_dir / '5_final_output.html'}")
    print(f"File size: {len(final_html)} bytes")
    
    final_issues = check_minimum_requirements(final_html)
    if final_issues:
        print(f"\n⚠ {len(final_issues)} validation issues remaining:")
        for issue in final_issues:
            print(f"   - {issue}")
    else:
        print("\n✓ All validation checks passed")
    
    return passed, final_html, output_dir