# runner.py
"""
CLI wrapper that:
- Loads environment variables
- Builds the LLM agents (using ChatPromptTemplate + ChatGoogleGenerativeAI)
- Parses CLI args, creates timestamped output folder and calls the orchestrator
"""

import os
import argparse
from pathlib import Path
from dotenv import load_dotenv

# imports for langchain-style chains (same as original)
from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI

# orchestrator import
from sim_generator import generate_simulation_with_checks

load_dotenv()  # load .env

def make_chain(prompt_template: str, llm_instance):
    prompt = ChatPromptTemplate.from_template(prompt_template)
    return prompt | llm_instance


def build_all_chains():
    planner_llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        temperature=0.3,
        api_key=os.getenv("GOOGLE_API_KEY")
    )

    creation_llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        temperature=0.2,
        api_key=os.getenv("GOOGLE_API_KEY"),
    )

    bugfix_llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash-lite",
        temperature=0.2,
        api_key=os.getenv("GOOGLE_API_KEY"),
    )

    student_interaction_llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash-lite",
        temperature=0.6,
        api_key=os.getenv("GOOGLE_API_KEY"),
    )

    incorporate_feedback_llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash-lite",
        temperature=0.2,
        api_key=os.getenv("GOOGLE_API_KEY"),
    )

    review_llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash-lite",
        temperature=0.1,
        api_key=os.getenv("GOOGLE_API_KEY"),
    )

    planner_prompt = """
You are the Simulation Planner Agent.
Convert the learning topic into a complete simulation blueprint for a CBSE Class 7 student (Moderate difficulty, mobile-first).

Input: spec.json content provided below:
{spec_json}

Instructions:
- Follow everything from the spec.json file
- Output should be mainly focused on visuals 
- Use less text and more images/graphics
- Leave no room for improvement
- Make it engaging and interactive

Produce a JSON blueprint containing:
1. learning_objectives (3-5)
2. key_concepts
3. variables_to_simulate (max 4)
4. user_interactions (sliders, buttons, drag - but assume simplest HTML controls)
5. simulation_logic (step-by-step behaviour)
6. mobile_ui_plan (vertical layout)
7. misconceptions_to_address
8. text_instructions_for_students (simple English)
9. file_target: "single_file_html"
10. safety_constraints

CRITICAL: Output ONLY valid JSON with NO markdown code blocks, NO extra text, NO commentary.

Example format:
{{
  "learning_objectives": [...],
  "key_concepts": [...],
  ...
}}

Output only JSON.
"""

    creation_prompt = """
You are the HTML Simulation Generator Agent.

Input blueprint:
{plan}

Instructions:
- Follow everything from the blueprint and don't skip any part of it
- Output should be mainly focused on visuals 
- Leave no room for improvement
- Make it engaging and interactive
- The simulation spuld feel like a experimantal lab and sjow experimental results
- The simulation should be completely self-contained and should not require any external resources
- The simulation should be complex enough and should not be too simple
- The simulation should be scientifically accurate and should not be too complex

Task:
- Produce a COMPLETE, RUNNABLE single-file HTML document
- Use inline styles and inline scripts for all functionality
- Include viewport meta tag: <meta name="viewport" content="width=device-width, initial-scale=1.0">
- Keep all text at 7th-grade reading level
- Do NOT leave placeholders or "Future Generator Note" comments
- Implement actual visuals and interactions (SVG graphics, color changes, animations)
- For each variable, create a working control (slider/button) and visual feedback
- Ensure touch targets are at least 44px
- Make it engaging and interactive

CRITICAL OUTPUT FORMAT:
You MUST output in this EXACT format with NO extra text:

{{
  "index.html": "<!DOCTYPE html>
<html>
<head>
    <meta charset=\"UTF-8\">
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">
    <title>Your Title</title>
    <style>
        /* Your CSS here */
    </style>
</head>
<body>
    <!-- Your HTML here -->
    <script>
        // Your JavaScript here
    </script>
</body>
</html>"
}}

CRITICAL: 
- Output ONLY the JSON object shown above
- NO markdown code blocks (no ```)
- NO extra commentary
- The entire HTML must be inside the "index.html" property as a string
- Escape quotes properly inside the HTML string
"""

    bugfix_prompt = """
You are the Bug-Fix Agent.

Input HTML content:
{html}

Task:
- Fix structural HTML errors
- Fix broken references
- Add missing viewport meta if absent
- Fix mobile-responsiveness issues
- Fix JavaScript syntax errors
- Ensure touch targets are >= 44px
- Keep file self-contained (no external resources)
- Maintain 7th-grade reading level

CRITICAL OUTPUT FORMAT:
You MUST output in this EXACT format:

{{
  "fixed": true,
  "index.html": "<!DOCTYPE html>...",
  "explanations": ["fix 1", "fix 2", ...]
}}

CRITICAL:
- Output ONLY valid JSON
- NO markdown code blocks (no ```)
- NO extra commentary
- The entire corrected HTML must be in the "index.html" property
"""

    student_interaction_prompt = """
You are the Student Interaction Agent for class 7 CBSE.

Original spec:
{spec_json}

Blueprint:
{plan}

Produce JSON with student questions and guidance.

CRITICAL OUTPUT FORMAT:
{{
  "intro": "2-3 line friendly intro",
  "questions": [
    {{
      "question": "...",
      "type": "mcq",
      "options": ["A) ...","B) ...","C) ...","D) ..."],
      "hint": "...",
      "correct_index": 0
    }}
  ],
  "followups": ["suggestion 1", "suggestion 2"],
  "summary": "Short learning summary"
}}

Requirements:
- Tone: Encouraging, age-appropriate
- Language: 7th-grade reading level
- Do NOT reveal correct answers in question text
- Output ONLY valid JSON, NO markdown blocks, NO commentary
"""

    incorporate_feedback_prompt = """
You are the Simulation Improvement Agent.

Input HTML:
{html}

Feedback:
{feedback_text}

Task:
Apply improvements based on feedback while keeping the file self-contained and mobile-first.

CRITICAL OUTPUT FORMAT:
{{
  "index.html": "<!DOCTYPE html>...",
  "changes_made": ["change 1", "change 2", ...]
}}

CRITICAL:
- Output ONLY valid JSON
- NO markdown code blocks
- NO extra commentary
"""

    review_prompt = """
You are the Review Agent for CBSE Class 7 simulations.

Input HTML:
{html}

Evaluate on these criteria (0-5 scale):

1. Pedagogical clarity (0-5)
2. Conceptual correctness (0-5)
3. Mobile responsiveness (0-5)
4. Interactivity quality (0-5)
5. Code reliability (0-5)
6. Safety & age appropriateness (0-5)

CRITICAL OUTPUT FORMAT:
{{
  "scores": {{
    "pedagogical_clarity": 0,
    "conceptual_correctness": 0,
    "mobile_responsiveness": 0,
    "interactivity_quality": 0,
    "code_reliability": 0,
    "safety_age_appropriateness": 0
  }},
  "pass": true,
  "required_changes": ["change 1", "change 2"],
  "return_to": "none"
}}

Pass criteria: all scores >= 3 and average >= 4

CRITICAL:
- Output ONLY valid JSON
- NO markdown code blocks
- NO extra commentary
"""

    planner_chain = make_chain(planner_prompt, planner_llm)
    creation_chain = make_chain(creation_prompt, creation_llm)
    bugfix_chain = make_chain(bugfix_prompt, bugfix_llm)
    student_interaction_chain = make_chain(student_interaction_prompt, student_interaction_llm)
    incorporate_feedback_chain = make_chain(incorporate_feedback_prompt, incorporate_feedback_llm)
    review_chain = make_chain(review_prompt, review_llm)

    return (
        planner_chain,
        creation_chain,
        bugfix_chain,
        student_interaction_chain,
        incorporate_feedback_chain,
        review_chain
    )


def main():
    parser = argparse.ArgumentParser(description="Run the CBSE Class 7 simulation generator.")
    parser.add_argument("--spec", "-s", type=str, default="spec.json",
                        help="Path to the spec JSON file.")
    parser.add_argument("--output-root", type=str, default="output",
                        help="Root directory where timestamped outputs will be saved.")
    parser.add_argument("--no-save-intermediates", action="store_true",
                        help="If set, do not save intermediate node outputs.")
    args = parser.parse_args()

    spec_path = args.spec
    output_root = args.output_root
    save_intermediates = not args.no_save_intermediates

    if not Path(spec_path).exists():
        print(f"Spec not found: {spec_path}")
        return

    print("Initializing LLM agents and chains...")
    chains = build_all_chains()

    success, html, output_folder = generate_simulation_with_checks(
        spec_path=spec_path,
        planner_chain=chains[0],
        creation_chain=chains[1],
        bugfix_chain=chains[2],
        student_interaction_chain=chains[3],
        incorporate_feedback_chain=chains[4],
        review_chain=chains[5],
        save_intermediates=save_intermediates,
        output_root=output_root,
    )

    print("\n" + "=" * 70)
    if success:
        print("✅ Simulation approved and ready for Class 7 students!")
    else:
        print("⚠ Simulation generated but needs revision.")
    print("=" * 70)
    print(f"📁 All outputs saved to: {output_folder}")
    print(f"📄 Main file: {output_folder / '5_final_output.html'}")
    print(f"\n💡 Open {output_folder / '5_final_output.html'} in a browser to view the simulation")


if __name__ == "__main__":
    main()