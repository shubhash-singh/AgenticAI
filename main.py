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
    """Load spec JSON - expects single concept format"""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def safe_json_parse(raw: Any) -> Dict[str, Any]:
    """Try to parse a JSON object from an LLM response."""
    if isinstance(raw, BaseMessage):
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

    if text.startswith("```"):
        text = text.strip("`").strip()
        if text.lower().startswith("json"):
            text = text[4:].lstrip()

    match = re.search(r'\{(?:[^{}]|(?:\{[^{}]*\}))*\}', text, re.DOTALL)
    if not match:
        first_brace = text.find('{')
        last_brace = text.rfind('}')
        if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
            json_str = text[first_brace:last_brace + 1]
        else:
            snippet = text[:300].replace("\n", "\\n")
            raise ValueError(
                f"safe_json_parse: Could not find JSON. First 300 chars: {snippet}"
            )
    else:
        json_str = match.group(0)

    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        snippet = json_str[:300].replace("\n", "\\n")
        raise ValueError(
            f"safe_json_parse: JSON decode failed. Error: {e}; snippet: {snippet}"
        ) from e


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


# ------------ Step 1: PLANNER NODE ------------

def build_planner_chain():
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash-lite",
        temperature=0.3,
        api_key=os.getenv("GOOGLE_API_KEY_PLANNING")
    )

    prompt = ChatPromptTemplate.from_template(
        """You are the Simulation Planner Agent.
Convert the learning topic into a complete simulation blueprint for a CBSE Class 7 student (Moderate difficulty, mobile-first).

Given Topic/Concept:
{spec_json}

Device: Mobile responsive (small screens, touch-friendly)

Produce a JSON blueprint containing:

1. learning_objectives: List 3-5 clear learning objectives appropriate for Class 7 CBSE
2. key_concepts: List the main concepts to be demonstrated
3. variables_to_simulate: Max 4 variables that students can control (e.g., temperature, speed, angle, size)
4. user_interactions: Describe sliders, buttons, or simple drag interactions (assume simplest HTML controls)
5. simulation_logic: Step-by-step behavior of how the simulation works
6. mobile_ui_plan: Describe vertical layout optimized for mobile screens
7. misconceptions_to_address: Common student misconceptions about this topic
8. text_instructions_for_students: Simple English instructions (7th grade reading level)
9. file_target: Always set to "single_file_html"
10. safety_constraints: Any safety considerations for the content

Output ONLY JSON in this exact structure:
{{
  "learning_objectives": ["objective 1", "objective 2", ...],
  "key_concepts": ["concept 1", "concept 2", ...],
  "variables_to_simulate": [
    {{"name": "variable_name", "min": X, "max": Y, "default": Z, "unit": "unit_name"}},
    ...
  ],
  "user_interactions": {{
    "sliders": ["description of slider 1", ...],
    "buttons": ["description of button 1", ...],
    "other": "description of any other interactions"
  }},
  "simulation_logic": [
    "Step 1: ...",
    "Step 2: ...",
    ...
  ],
  "mobile_ui_plan": {{
    "layout": "vertical single column",
    "sections": ["section 1", "section 2", ...],
    "touch_targets": "minimum 44px"
  }},
  "misconceptions_to_address": ["misconception 1", ...],
  "text_instructions_for_students": "Simple, clear instructions in 2-3 sentences",
  "file_target": "single_file_html",
  "safety_constraints": ["constraint 1", ...]
}}

Make it engaging, age-appropriate, and scientifically accurate for CBSE Class 7."""
    )

    return prompt | llm


# ------------ Step 2: CREATOR NODE ------------

def build_creation_chain():
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash-lite",
        temperature=0.2,
        api_key=os.getenv("GOOGLE_API_KEY_BUILDING"),
    )

    prompt = ChatPromptTemplate.from_template(
"""You are the HTML Simulation Generator Agent.

Input: Planner Node JSON blueprint
{plan}

Original Concept:
{spec_json}

Task:
- Produce a single self-contained file named index.html
- Use inline styles (inside <style> tag) and inline scripts (inside <script> tag at end of body)
- NO external libraries, NO external CSS/JS files
- Prefer progressive enhancement: core functionality as HTML (inputs, labels, static illustrations)
- If brief JS is necessary for basic interaction (toggles, calculations, touch hints), embed it in <script> tag
- Keep all text at 7th-grade reading level (simple, clear language)
- Keep file size small
- Provide explanatory comments in HTML where interactive logic should work

STRUCTURE REQUIREMENTS:

<!doctype html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>[Concept Name] - Interactive Simulation</title>
  <style>
    /* CSS Variables for theming */
    :root {{
      --primary: #3b82f6;
      --secondary: #10b981;
      --danger: #ef4444;
      --bg: #f8fafc;
      --card: #ffffff;
      --text: #1e293b;
      --text-light: #64748b;
      --border: #e2e8f0;
    }}

    * {{
      margin: 0;
      padding: 0;
      box-sizing: border-box;
    }}

    body {{
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
      background: var(--bg);
      color: var(--text);
      line-height: 1.6;
      padding: 1rem;
    }}

    .container {{
      max-width: 600px;
      margin: 0 auto;
    }}

    header {{
      background: var(--card);
      padding: 1.5rem;
      border-radius: 12px;
      box-shadow: 0 2px 8px rgba(0,0,0,0.1);
      margin-bottom: 1rem;
      text-align: center;
    }}

    h1 {{
      color: var(--primary);
      font-size: 1.5rem;
      margin-bottom: 0.5rem;
    }}

    .card {{
      background: var(--card);
      padding: 1.25rem;
      border-radius: 12px;
      box-shadow: 0 2px 8px rgba(0,0,0,0.1);
      margin-bottom: 1rem;
    }}

    .instructions {{
      background: #eff6ff;
      border-left: 4px solid var(--primary);
      padding: 1rem;
      border-radius: 8px;
      margin-bottom: 1rem;
      font-size: 0.95rem;
    }}

    /* Simulation Area */
    .simulation-area {{
      background: #f1f5f9;
      border: 2px solid var(--border);
      border-radius: 12px;
      padding: 1.5rem;
      min-height: 250px;
      display: flex;
      align-items: center;
      justify-content: center;
      position: relative;
    }}

    /* Controls */
    .controls {{
      margin-top: 1rem;
    }}

    .control-group {{
      margin-bottom: 1.25rem;
    }}

    .control-label {{
      display: flex;
      justify-content: space-between;
      margin-bottom: 0.5rem;
      font-weight: 600;
      font-size: 0.95rem;
    }}

    .control-value {{
      color: var(--primary);
      background: #eff6ff;
      padding: 0.25rem 0.5rem;
      border-radius: 4px;
    }}

    input[type="range"] {{
      width: 100%;
      height: 8px;
      border-radius: 4px;
      background: #cbd5e1;
      outline: none;
      -webkit-appearance: none;
    }}

    input[type="range"]::-webkit-slider-thumb {{
      -webkit-appearance: none;
      width: 24px;
      height: 24px;
      border-radius: 50%;
      background: var(--primary);
      cursor: pointer;
      box-shadow: 0 2px 4px rgba(0,0,0,0.2);
    }}

    input[type="range"]::-moz-range-thumb {{
      width: 24px;
      height: 24px;
      border-radius: 50%;
      background: var(--primary);
      cursor: pointer;
      border: none;
    }}

    /* Buttons */
    .button-group {{
      display: flex;
      gap: 0.75rem;
      margin-top: 1rem;
    }}

    button {{
      flex: 1;
      padding: 0.875rem;
      font-size: 1rem;
      font-weight: 600;
      border: none;
      border-radius: 8px;
      cursor: pointer;
      transition: all 0.2s;
      min-height: 44px;
    }}

    .btn-primary {{
      background: var(--primary);
      color: white;
    }}

    .btn-primary:hover {{
      background: #2563eb;
      transform: translateY(-1px);
    }}

    .btn-primary:active {{
      transform: translateY(0);
    }}

    .btn-secondary {{
      background: var(--border);
      color: var(--text);
    }}

    .btn-secondary:hover {{
      background: #cbd5e1;
    }}

    /* Status Display */
    .status {{
      padding: 0.75rem;
      border-radius: 8px;
      text-align: center;
      font-weight: 600;
      margin-top: 1rem;
    }}

    .status.info {{ background: #dbeafe; color: #1e40af; }}
    .status.success {{ background: #dcfce7; color: #166534; }}
    .status.warning {{ background: #fef3c7; color: #92400e; }}

    /* Questions */
    .question {{
      background: #f8fafc;
      padding: 1rem;
      border-radius: 8px;
      margin-top: 1rem;
    }}

    .question h3 {{
      color: var(--primary);
      font-size: 1.1rem;
      margin-bottom: 0.75rem;
    }}

    .options {{
      display: flex;
      flex-direction: column;
      gap: 0.5rem;
    }}

    .option {{
      padding: 0.75rem;
      background: white;
      border: 2px solid var(--border);
      border-radius: 8px;
      cursor: pointer;
      transition: all 0.2s;
    }}

    .option:hover {{
      border-color: var(--primary);
      background: #eff6ff;
    }}

    .option.correct {{
      background: #dcfce7;
      border-color: var(--secondary);
    }}

    .option.incorrect {{
      background: #fee2e2;
      border-color: var(--danger);
    }}

    /* Responsive */
    @media (max-width: 480px) {{
      body {{ padding: 0.5rem; }}
      h1 {{ font-size: 1.25rem; }}
      .card {{ padding: 1rem; }}
    }}
  </style>
</head>
<body>

<div class="container">
  <header>
    <h1>[Concept Title from blueprint]</h1>
    <p>[Brief description - 7th grade level]</p>
  </header>

  <div class="card">
    <div class="instructions">
      📚 <strong>Instructions:</strong> [Step-by-step instructions from blueprint]
    </div>
  </div>

  <!-- Simulation Visualization Area -->
  <div class="card">
    <h2>Interactive Simulation</h2>
    <div class="simulation-area" id="simArea">
      <!-- Visual representation goes here -->
      <!-- Use SVG or HTML elements to show the concept -->
      <!-- Add comments explaining what should happen -->
    </div>

    <!-- Controls Section -->
    <div class="controls">
      <h3>Controls</h3>
      
      <!-- Generate sliders based on variables_to_simulate from blueprint -->
      <div class="control-group">
        <div class="control-label">
          <span>[Variable Name]</span>
          <span class="control-value" id="value1Display">[default]</span>
        </div>
        <input type="range" id="slider1" min="X" max="Y" value="Z" step="1">
      </div>

      <!-- Repeat for each variable -->

      <!-- Buttons -->
      <div class="button-group">
        <button class="btn-primary" id="startBtn">▶ Start</button>
        <button class="btn-secondary" id="resetBtn">↺ Reset</button>
      </div>

      <div class="status info" id="statusDisplay">
        Ready to start!
      </div>
    </div>
  </div>

  <!-- Key Concepts -->
  <div class="card">
    <h2>What's Happening?</h2>
    <p>[Explain the concept being demonstrated - simple language]</p>
    <ul>
      <li>[Key point 1]</li>
      <li>[Key point 2]</li>
      <li>[Key point 3]</li>
    </ul>
  </div>

  <!-- Learning Questions -->
  <div class="card">
    <h2>Test Your Understanding</h2>
    <div class="question">
      <h3>Question 1: [Question text]</h3>
      <div class="options">
        <div class="option" data-correct="false">A) [Option]</div>
        <div class="option" data-correct="true">B) [Option]</div>
        <div class="option" data-correct="false">C) [Option]</div>
        <div class="option" data-correct="false">D) [Option]</div>
      </div>
    </div>
  </div>
</div>

<script>
  // === INITIALIZATION ===
  function init() {{
    // Get DOM elements
    const startBtn = document.getElementById('startBtn');
    const resetBtn = document.getElementById('resetBtn');
    const slider1 = document.getElementById('slider1');
    const statusDisplay = document.getElementById('statusDisplay');
    
    // Event listeners
    if (startBtn) startBtn.addEventListener('click', startSimulation);
    if (resetBtn) resetBtn.addEventListener('click', resetSimulation);
    if (slider1) slider1.addEventListener('input', updateSlider1);
    
    // Question handling
    document.querySelectorAll('.option').forEach(option => {{
      option.addEventListener('click', checkAnswer);
    }});
    
    // Initial update
    updateDisplay();
  }}

  // === SLIDER HANDLERS ===
  function updateSlider1(e) {{
    const value = e.target.value;
    document.getElementById('value1Display').textContent = value + ' [unit]';
    updateDisplay();
  }}

  // === SIMULATION CONTROL ===
  let animationRunning = false;
  let animationId = null;

  function startSimulation() {{
    if (animationRunning) return;
    animationRunning = true;
    
    document.getElementById('startBtn').disabled = true;
    document.getElementById('statusDisplay').textContent = 'Simulation Running...';
    document.getElementById('statusDisplay').className = 'status warning';
    
    animate();
  }}

  function animate() {{
    if (!animationRunning) return;
    
    // Animation logic here
    // Update visual elements based on time or slider values
    
    animationId = requestAnimationFrame(animate);
  }}

  function resetSimulation() {{
    animationRunning = false;
    if (animationId) cancelAnimationFrame(animationId);
    
    document.getElementById('startBtn').disabled = false;
    document.getElementById('statusDisplay').textContent = 'Ready to start!';
    document.getElementById('statusDisplay').className = 'status info';
    
    // Reset visuals to initial state
    updateDisplay();
  }}

  // === VISUAL UPDATES ===
  function updateDisplay() {{
    // Read slider values
    const value1 = document.getElementById('slider1')?.value || 0;
    
    // Update visual elements based on current values
    // Modify SVG/HTML elements in simulation area
  }}

  // === QUESTION HANDLING ===
  function checkAnswer(e) {{
    const option = e.target;
    const isCorrect = option.dataset.correct === 'true';
    
    // Disable all options in this question
    const allOptions = option.parentElement.querySelectorAll('.option');
    allOptions.forEach(opt => {{
      opt.style.pointerEvents = 'none';
      if (opt.dataset.correct === 'true') {{
        opt.classList.add('correct');
      }}
    }});
    
    // Mark selected answer
    if (!isCorrect) {{
      option.classList.add('incorrect');
    }}
  }}

  // === START ON LOAD ===
  document.addEventListener('DOMContentLoaded', init);
</script>

</body>
</html>

IMPORTANT REQUIREMENTS:
1. Make it scientifically accurate for the concept
2. Use simple 7th-grade language throughout
3. Include helpful comments for future improvements
4. Ensure touch-friendly controls (44px minimum)
5. Progressive enhancement - works without JS for basic content
6. Address misconceptions from the blueprint
7. Make the visual simulation area actually show the concept

Output ONLY JSON:
{{
  "index.html": "<!doctype html>...full HTML content..."
}}

If blueprint lacks detail, make sensible grade-appropriate assumptions."""
    )

    return prompt | llm


# ------------ Step 3: BUGFIX NODE ------------

def build_bugfix_chain():
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash-lite",
        temperature=0.2,
        api_key=os.getenv("GOOGLE_API_KEY_BUGFIX"),
    )

    prompt = ChatPromptTemplate.from_template(
"""You are the Bug-Fix Agent.

Input: Single-file index.html
{html}

Task:
- Parse the provided index.html
- Fix structural HTML errors, broken references inside the file, missing IDs
- Fix ARIA attributes for accessibility
- Fix mobile-responsiveness issues (viewport meta, touch target sizes minimum 44px)
- If inline <script> exists, fix syntax errors and missing DOM element references
- Do NOT add large new logic - only minimal corrections for page to render and basic interactions to work
- Ensure no console errors after fixes
- Do not split file into separate assets
- Maintain single-file structure

Output JSON:
{{
  "fixed": true/false,
  "index.html": "<!doctype html>...corrected file...",
  "explanations": ["fix 1", "fix 2", ...]
}}"""
    )

    return prompt | llm


# ------------ Step 4: STUDENT INTERACTION NODE ------------

def build_student_interaction_chain():
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash-lite",
        temperature=0.6,
        api_key=os.getenv("GOOGLE_API_KEY_BUGFIX")
    )

    prompt = ChatPromptTemplate.from_template(
"""You are the Student Interaction Agent for Class 7 CBSE.

Input topic/concept:
{spec_json}

Simulation description:
{plan}

Produce JSON for student engagement:

{{
  "intro": "2-3 line friendly intro in simple language",
  "questions": [
    {{
      "question": "Clear question about the concept",
      "type": "mcq",
      "options": ["A) option", "B) option", "C) option", "D) option"],
      "hint": "Helpful hint if student is stuck",
      "correct_index": 0
    }},
    {{
      "question": "Prediction question",
      "type": "prediction",
      "options": ["A) option", "B) option", "C) option"],
      "hint": "Think about what you observed",
      "correct_index": 1
    }}
  ],
  "followups": [
    "Interesting followup question 1",
    "Thought-provoking followup 2"
  ],
  "summary": "Short learning summary in 1-2 lines"
}}

Requirements:
- Tone: Encouraging, age-appropriate for 12-13 year olds
- Language: Simple 7th grade reading level
- Do NOT reveal correct answers in intro/questions text
- Store correct answers only in correct_index field
- Make questions relevant to what they see in simulation
- Address common misconceptions

Output ONLY JSON."""
    )

    return prompt | llm


# ------------ Step 5: INCORPORATE FEEDBACK NODE ------------

def build_incorporate_feedback_chain():
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash-lite",
        temperature=0.2,
        api_key=os.getenv("GOOGLE_API_KEY_BUGFIX")
    )

    prompt = ChatPromptTemplate.from_template(
"""You are the Simulation Improvement Agent.

Input single-file HTML:
{html}

Feedback to incorporate:
{feedback_text}

Tasks:
1. Identify what must change inside the single-file HTML based on feedback
2. Apply minimal inline edits:
   - Update HTML structure
   - Improve text clarity
   - Adjust inline styles for better readability
   - Small inline JS tweaks if needed
3. Keep file self-contained
4. Maintain mobile-first responsive design
5. Keep 7th grade reading level

Output JSON:
{{
  "index.html": "<!doctype html>...updated file...",
  "changes_made": ["change 1", "change 2", ...]
}}

Do NOT add external dependencies. Make targeted improvements only."""
    )

    return prompt | llm


# ------------ Step 6: REVIEW NODE ------------

def build_review_chain():
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash-lite",
        temperature=0.1,
        api_key=os.getenv("GOOGLE_API_KEY_BUGFIX")
    )

    prompt = ChatPromptTemplate.from_template(
"""You are the Review Agent for CBSE Class 7 simulations.

Input: Single-file index.html
{html}

Evaluate on these criteria (0-5 scale):

1. Pedagogical clarity (0-5)
   - Are learning objectives clear?
   - Is the concept well-explained?
   - Is language appropriate for Class 7?

2. Conceptual correctness (0-5)
   - Is the science/concept accurate?
   - Are there any misconceptions?
   - Is it aligned with CBSE curriculum?

3. Mobile responsiveness (0-5)
   - Does it work on small screens?
   - Are touch targets ≥ 44px?
   - Is layout vertical/single-column?
   - Is viewport meta tag present?

4. Interactivity quality (0-5)
   - Do controls work smoothly?
   - Is the simulation engaging?
   - Are interactions intuitive?

5. Code reliability (0-5)
   - Valid HTML structure?
   - No console errors?
   - Inline scripts work correctly?
   - No broken references?

6. Safety & age appropriateness (0-5)
   - Content appropriate for 12-13 year olds?
   - No safety concerns?
   - Encouraging and positive tone?

Output JSON:
{{
  "scores": {{
    "pedagogical_clarity": X,
    "conceptual_correctness": X,
    "mobile_responsiveness": X,
    "interactivity_quality": X,
    "code_reliability": X,
    "safety_age_appropriateness": X
  }},
  "pass": true/false,
  "required_changes": ["change 1", "change 2", ...],
  "return_to": "planner/creator/bugfix/none"
}}

Pass criteria: All scores ≥ 3, average ≥ 4
If pass=false, indicate whether to return to:
- "planner": concept/UI issues
- "creator": implementation issues  
- "bugfix": minor fixes needed
- "none": if pass=true"""
    )

    return prompt | llm


# ------------ Orchestrator ------------

def generate_simulation_with_checks(
    spec_path: str,
    output_path: str = "index.html",
    save_intermediates: bool = True,
) -> Tuple[bool, str]:
    """Generate CBSE Class 7 single-file simulation."""
    
    print("=" * 70)
    print("CBSE CLASS 7 SIMULATION GENERATOR (Single-File HTML)")
    print("=" * 70)
    
    # 1. Load spec
    print("\n[1/6] Loading concept...")
    try:
        spec = load_spec(spec_path)
        spec_json = json.dumps(spec, indent=2, ensure_ascii=False)
        concept_name = spec.get('Concept', 'Unknown Concept')
        print(f"✓ Concept: {concept_name}")
    except Exception as e:
        print(f"✗ Failed to load: {e}")
        return False, ""

    # 2. Build chains
    print("\n[2/6] Initializing agents...")
    try:
        planner_chain = build_planner_chain()
        creation_chain = build_creation_chain()
        bugfix_chain = build_bugfix_chain()
        student_interaction_chain = build_student_interaction_chain()
        incorporate_feedback_chain = build_incorporate_feedback_chain()
        review_chain = build_review_chain()
        print("✓ All agents initialized")
    except Exception as e:
        print(f"✗ Init failed: {e}")
        return False, ""

    # 3. PLANNER NODE
    print("\n[3/6] Planning simulation (Planner Agent)...")
    try:
        plan_response = planner_chain.invoke({"spec_json": spec_json})
        plan_data = safe_json_parse(plan_response.content)
        plan_json = json.dumps(plan_data, indent=2, ensure_ascii=False)
        
        if save_intermediates:
            Path("1_planner_blueprint.json").write_text(plan_json, encoding="utf-8")
        
        print("✓ Blueprint created")
        print(f"   Objectives: {len(plan_data.get('learning_objectives', []))}")
        print(f"   Variables: {len(plan_data.get('variables_to_simulate', []))}")
    except Exception as e:
        print(f"✗ Planning failed: {e}")
        return False, ""

    # 4. CREATOR NODE
    print("\n[4/6] Creating index.html (Creator Agent)...")
    try:
        creation_response = creation_chain.invoke({
            "spec_json": spec_json, 
            "plan": plan_json
        })
        creation_data = safe_json_parse(creation_response.content)
        html = creation_data.get("index.html", "")

        if save_intermediates:
            Path("2_creator_output.html").write_text(html, encoding="utf-8")

        issues = check_minimum_requirements(html)
        if issues:
            print("⚠ Initial issues:")
            for issue in issues:
                print(f"   - {issue}")
        else:
            print("✓ Basic validation passed")
            
    except Exception as e:
        print(f"✗ Creation failed: {e}")
        return False, ""

    # 5. BUGFIX NODE
    print("\n[5/6] Fixing issues (Bugfix Agent)...")
    try:
        bugfix_response = bugfix_chain.invoke({"html": html})
        bugfix_data = safe_json_parse(bugfix_response.content)
        html = bugfix_data.get("index.html", html)
        
        if bugfix_data.get("fixed", False):
            explanations = bugfix_data.get("explanations", [])
            print(f"✓ Fixed {len(explanations)} issues:")
            for exp in explanations[:3]:  # Show first 3
                print(f"   - {exp}")
        else:
            print("✓ No critical bugs found")
            
        if save_intermediates:
            Path("3_bugfix_output.html").write_text(html, encoding="utf-8")
            
    except Exception as e:
        print(f"⚠ Bugfix error: {e}")

    # 6. STUDENT INTERACTION NODE  
    print("\n[6/6] Generating student questions (Student Interaction Agent)...")
    try:
        interaction_response = student_interaction_chain.invoke({
            "spec_json": spec_json,
            "plan": plan_json
        })
        interaction_data = safe_json_parse(interaction_response.content)
        
        if save_intermediates:
            Path("4_student_interaction.json").write_text(
                json.dumps(interaction_data, indent=2), 
                encoding="utf-8"
            )
        
        print(f"✓ Generated {len(interaction_data.get('questions', []))} questions")
        print(f"   Summary: {interaction_data.get('summary', 'N/A')[:50]}...")
        
    except Exception as e:
        print(f"⚠ Interaction generation error: {e}")
        interaction_data = {}

    # 7. REVIEW NODE
    print("\n" + "=" * 70)
    print("REVIEW (Review Agent)")
    print("=" * 70)
    try:
        review_response = review_chain.invoke({"html": html})
        review_data = safe_json_parse(review_response.content)

        scores = review_data.get("scores", {})
        passed = review_data.get("pass", False)
        required_changes = review_data.get("required_changes", [])
        return_to = review_data.get("return_to", "none")
        
        print(f"\nScores:")
        for criterion, score in scores.items():
            status = "✓" if score >= 3 else "✗"
            print(f"  {status} {criterion}: {score}/5")
        
        avg_score = sum(scores.values()) / len(scores) if scores else 0
        print(f"\nAverage Score: {avg_score:.2f}/5.0")
        print(f"Status: {'✅ APPROVED' if passed else '❌ NEEDS REVISION'}")
        
        if not passed:
            print(f"Return to: {return_to.upper()}")
            print("Required changes:")
            for change in required_changes[:5]:
                print(f"  - {change}")
        
    except Exception as e:
        print(f"⚠ Review failed: {e}")
        passed = False

    # 8. Save final output
    output_file = Path(output_path)
    output_file.write_text(html, encoding="utf-8")
    
    if save_intermediates:
        Path("5_final_output.html").write_text(html, encoding="utf-8")
        
        # Save review results
        if 'review_data' in locals():
            Path("6_review_results.json").write_text(
                json.dumps(review_data, indent=2),
                encoding="utf-8"
            )

    final_issues = check_minimum_requirements(html)
    
    print("\n" + "=" * 70)
    print("GENERATION COMPLETE")
    print("=" * 70)
    print(f"Output: {output_file.absolute()}")
    print(f"File size: {len(html)} bytes")
    
    if final_issues:
        print(f"\n⚠ {len(final_issues)} validation issues:")
        for issue in final_issues:
            print(f"   - {issue}")
    else:
        print("\n✓ All validation checks passed")
    
    return passed, html


# ------------ CLI entry ------------

if __name__ == "__main__":
    base_dir = Path(__file__).parent
    spec_path = base_dir / "spec.json"
    output_path = base_dir / "index.html"

    success, html = generate_simulation_with_checks(
        spec_path=str(spec_path),
        output_path=str(output_path),
        save_intermediates=True,
    )

    print(f"\n{'=' * 70}")
    if success:
        print("✅ Simulation approved and ready for Class 7 students!")
    else:
        print("⚠ Simulation generated but needs revision.")
    print(f"{'=' * 70}\n")
    print(f"📄 Open {output_path} in a browser to test the simulation.")