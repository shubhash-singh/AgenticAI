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
    """Enhanced validation checks."""
    issues = []

    if 'id="simCanvas"' not in html and "id='simCanvas'" not in html:
        issues.append("Missing main SVG element with id='simCanvas'.")

    range_count = html.count('<input type="range"')
    if range_count < 2:
        issues.append(f"Expected at least 2 sliders, found {range_count}.")

    # Check for start/reset buttons
    has_start = 'id="startBtn"' in html or 'id="start-btn"' in html or 'onclick="startSimulation' in html
    has_reset = 'id="resetBtn"' in html or 'id="reset-btn"' in html or 'onclick="resetSimulation' in html
    
    if not has_start:
        issues.append("Missing Start button.")
    if not has_reset:
        issues.append("Missing Reset button.")

    has_interaction = any(handler in html for handler in [
        "pointerdown", "mousedown", "touchstart", "onclick", "addEventListener"
    ])
    if not has_interaction:
        issues.append("No interaction handlers found.")

    if "updateSimulation" not in html:
        issues.append("Missing updateSimulation() function.")
    
    if "initSimulation" not in html or "DOMContentLoaded" not in html:
        issues.append("Missing proper initialization.")

    if "<!DOCTYPE html>" not in html:
        issues.append("Missing DOCTYPE.")
    
    if '<meta name="viewport"' not in html:
        issues.append("Missing viewport meta tag.")

    return issues


# ------------ Step 1: Planner chain ------------

def build_planner_chain():
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash-lite",
        temperature=0.3,
        api_key=os.getenv("GOOGLE_API_KEY_PLANNING")
    )

    prompt = ChatPromptTemplate.from_template(
        """You are an expert at designing animated educational simulations. Create a detailed visual plan.

Concept to visualize:
{spec_json}

Create a plan for a HIGHLY VISUAL, ANIMATED simulation:

# Primary Visual Animation
[Describe the MAIN thing that will animate/move when Start is clicked]
- What object/element animates?
- What type of motion? (rotation, translation, color change, size change, flow)
- Starting state vs. animated state
- How does it demonstrate the concept?

Example for "Flow of Heat":
- Two colored rectangles (hot=red, cold=blue)
- Animated particles flow from red to blue
- Colors gradually equalize
- Shows heat transfer visually

# SVG Canvas (500x350 viewBox)
Main animated objects:
1. [Object 1]: position (x,y), initial state, how it animates
2. [Object 2]: position (x,y), initial state, how it animates

Supporting elements:
- Background/grid
- Labels with live values
- Visual indicators (arrows, particles, trails)

Color scheme:
- Hot/Active: #ef4444 (red)
- Cold/Inactive: #3b82f6 (blue)
- Neutral: #6b7280 (gray)
- Highlight: #f59e0b (orange)

# Control Buttons
Start Button:
  - Text: "▶ Start Animation"
  - Action: Begin continuous animation
  - Disabled during animation
  - Updates to "⏸ Running..." when active

Reset Button:
  - Text: "↺ Reset"
  - Action: Stop animation, return to initial state
  - Always enabled

# Interactive Sliders
Slider 1: [Parameter Name] (e.g., "Temperature Difference")
  - Range: min to max (with units)
  - Default value
  - Real-time effect: [How it changes the visual]
  - Example: "Higher value = faster particle flow"

Slider 2: [Parameter Name] (e.g., "Object Size")
  - Range: min to max (with units)
  - Default value
  - Real-time effect: [How it changes the visual]

# Animation Logic (SPECIFIC)
Initial state:
  - [Describe exact positions, colors, sizes]

When Start is clicked:
  1. Set animationRunning = true
  2. Start requestAnimationFrame loop
  3. Each frame: [specific updates, e.g., "move particles 2px, fade colors by 1%"]
  4. Stop condition: [when to end, e.g., "after 10 seconds" or "when colors match"]

When Reset is clicked:
  1. Set animationRunning = false
  2. cancelAnimationFrame
  3. Reset all positions/colors/values to initial state
  4. Reset sliders to default

When Slider changes (during animation or paused):
  - Update [specific parameter]
  - Immediately reflect in visual

# Real-time Value Displays
- Display next to each slider: "[value] [unit]"
- Status text: "Ready" / "Running" / "Complete"
- Live calculated values: [e.g., "Heat transferred: X joules"]

# Educational Content
Key insight the animation reveals:
[What students should observe and learn]

Quiz questions referencing the animation:
1. Q: [Question about what they see]
   A: [Answer]
2. Q: [Question about relationship]
   A: [Answer]

Be ULTRA-SPECIFIC with positions, colors, and motion."""
    )

    return prompt | llm


# ------------ Step 2: Creation chain ------------

def build_creation_chain():
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash-lite",
        temperature=0.2,
        api_key=os.getenv("GOOGLE_API_KEY_BUILDING"),
    )

    prompt = ChatPromptTemplate.from_template(
"""You are an expert at creating beautiful, ANIMATED educational simulations. Generate complete HTML.

=== CRITICAL: ANIMATION IS MANDATORY ===
The simulation MUST have continuous, smooth animation when Start is clicked.
NOT just a static visual that changes once - actual MOVING, FLOWING, ANIMATING elements.

=== MOBILE-FIRST STRUCTURE ===
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>[Concept Name] Simulator</title>
  <style>
    :root {{
      --bg: #f7fafc;
      --card: #ffffff;
      --accent: #3b82f6;
      --accent-light: #93c5fd;
      --text-primary: #1f2937;
      --text-secondary: #6b7280;
      --success: #10b981;
      --error: #ef4444;
      --running: #f59e0b;
      --hot: #ef4444;
      --cold: #3b82f6;
    }}

    * {{ margin: 0; padding: 0; box-sizing: border-box; }}

    body {{
      font-family: system-ui, -apple-system, sans-serif;
      background: var(--bg);
      color: var(--text-primary);
      padding: 1rem;
      line-height: 1.6;
    }}

    .container {{
      max-width: 720px;
      margin: 0 auto;
    }}

    header {{
      text-align: center;
      padding: 1.5rem;
      background: var(--card);
      border-radius: 12px;
      margin-bottom: 1rem;
      box-shadow: 0 4px 12px rgba(0,0,0,0.06);
    }}

    h1 {{
      font-size: 1.8rem;
      color: var(--accent);
      margin-bottom: 0.5rem;
    }}

    .card {{
      background: var(--card);
      padding: 1rem;
      border-radius: 12px;
      box-shadow: 0 4px 12px rgba(0,0,0,0.06);
      margin-bottom: 1rem;
    }}

    /* SVG Canvas */
    #simCanvas {{
      width: 100%;
      height: auto;
      border-radius: 8px;
      background: #fdfdfd;
      border: 1px solid #e5e7eb;
    }}

    /* Button Styles */
    .button-group {{
      display: flex;
      gap: 0.5rem;
      margin-bottom: 1rem;
    }}

    .btn {{
      flex: 1;
      min-height: 44px;
      border: none;
      border-radius: 8px;
      font-size: 1rem;
      font-weight: 600;
      cursor: pointer;
      transition: all 0.2s;
    }}

    .btn-primary {{
      background: var(--accent);
      color: white;
    }}

    .btn-primary:hover {{
      background: #2563eb;
      transform: translateY(-1px);
    }}

    .btn-primary:disabled {{
      background: var(--running);
      cursor: not-allowed;
    }}

    .btn-secondary {{
      background: #e5e7eb;
      color: var(--text-primary);
    }}

    .btn-secondary:hover {{
      background: #d1d5db;
    }}

    /* Slider Controls */
    .control-group {{
      margin-bottom: 1rem;
    }}

    .control-header {{
      display: flex;
      justify-content: space-between;
      margin-bottom: 0.5rem;
    }}

    .control-label {{
      font-weight: 600;
      color: var(--text-primary);
    }}

    .control-value {{
      font-weight: 600;
      color: var(--accent);
      background: var(--accent-light);
      padding: 2px 8px;
      border-radius: 4px;
    }}

    input[type="range"] {{
      width: 100%;
      height: 8px;
      -webkit-appearance: none;
      appearance: none;
      background: #d1d5db;
      border-radius: 4px;
      cursor: pointer;
    }}

    input[type="range"]::-webkit-slider-thumb {{
      -webkit-appearance: none;
      width: 20px;
      height: 20px;
      background: var(--accent);
      border-radius: 50%;
      cursor: pointer;
      box-shadow: 0 2px 4px rgba(0,0,0,0.2);
    }}

    input[type="range"]::-moz-range-thumb {{
      width: 20px;
      height: 20px;
      background: var(--accent);
      border-radius: 50%;
      cursor: pointer;
      border: none;
    }}

    /* Status Display */
    .status {{
      text-align: center;
      padding: 0.75rem;
      border-radius: 8px;
      font-weight: 600;
      margin-bottom: 1rem;
    }}

    .status.ready {{ background: #e0f2fe; color: #0369a1; }}
    .status.running {{ background: #fef3c7; color: #92400e; }}
    .status.complete {{ background: #d1fae5; color: #065f46; }}

    /* Stats Grid */
    .stats-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
      gap: 0.75rem;
      margin-top: 1rem;
    }}

    .stat-card {{
      padding: 0.75rem;
      background: #f9fafb;
      border-radius: 8px;
      border: 1px solid #e5e7eb;
    }}

    .stat-label {{
      font-size: 0.85rem;
      color: var(--text-secondary);
      margin-bottom: 0.25rem;
    }}

    .stat-value {{
      font-size: 1.25rem;
      font-weight: 700;
      color: var(--accent);
    }}
  </style>
</head>
<body>

<div class="container">
  <header>
    <h1>[Concept Title]</h1>
    <p>[Brief description from spec]</p>
  </header>

  <!-- Visualization Card -->
  <div class="card">
    <h2>Visual Simulation</h2>
    <svg id="simCanvas" viewBox="0 0 500 350">
      <!-- Create animated SVG elements here based on plan -->
      <!-- Example: particles, shapes, gradients that MOVE -->
    </svg>
  </div>

  <!-- Controls Card -->
  <div class="card">
    <h2>Controls</h2>
    
    <div class="status ready" id="statusDisplay">Ready to Start</div>

    <div class="button-group">
      <button id="startBtn" class="btn btn-primary">▶ Start Animation</button>
      <button id="resetBtn" class="btn btn-secondary">↺ Reset</button>
    </div>

    <div class="control-group">
      <div class="control-header">
        <span class="control-label">[Slider 1 Name]</span>
        <span class="control-value" id="slider1Val">[default]</span>
      </div>
      <input type="range" id="slider1" min="X" max="Y" value="Z" step="S">
    </div>

    <div class="control-group">
      <div class="control-header">
        <span class="control-label">[Slider 2 Name]</span>
        <span class="control-value" id="slider2Val">[default]</span>
      </div>
      <input type="range" id="slider2" min="X" max="Y" value="Z" step="S">
    </div>

    <div class="stats-grid">
      <div class="stat-card">
        <div class="stat-label">[Stat 1]</div>
        <div class="stat-value" id="stat1">0</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">[Stat 2]</div>
        <div class="stat-value" id="stat2">0</div>
      </div>
    </div>
  </div>

  <!-- Educational Content -->
  <div class="card">
    <h2>Key Concepts</h2>
    <p>[Explanation referencing the animation]</p>
  </div>
</div>

<script>
  // === STATE MANAGEMENT ===
  let animationState = {{
    isRunning: false,
    animationId: null,
    startTime: 0,
    // Add other state variables
  }};

  // === INITIALIZATION ===
  function initSimulation() {{
    // Get DOM elements
    const startBtn = document.getElementById('startBtn');
    const resetBtn = document.getElementById('resetBtn');
    const slider1 = document.getElementById('slider1');
    const slider2 = document.getElementById('slider2');
    const statusDisplay = document.getElementById('statusDisplay');
    
    // Button event listeners
    startBtn.addEventListener('click', startAnimation);
    resetBtn.addEventListener('click', resetSimulation);
    
    // Slider event listeners
    slider1.addEventListener('input', handleSlider1Change);
    slider2.addEventListener('input', handleSlider2Change);
    
    // Initial render
    updateSimulation();
  }}

  // === ANIMATION CONTROL ===
  function startAnimation() {{
    if (animationState.isRunning) return;
    
    animationState.isRunning = true;
    animationState.startTime = Date.now();
    
    const startBtn = document.getElementById('startBtn');
    const statusDisplay = document.getElementById('statusDisplay');
    
    startBtn.disabled = true;
    startBtn.textContent = '⏸ Running...';
    statusDisplay.textContent = 'Animation Running';
    statusDisplay.className = 'status running';
    
    animate();
  }}

  function animate() {{
    if (!animationState.isRunning) return;
    
    const elapsed = Date.now() - animationState.startTime;
    
    // === ANIMATION CALCULATIONS ===
    // Update positions, colors, values based on elapsed time
    // Example: 
    // const progress = (elapsed / 5000) % 1; // 5 second cycle
    // updateVisuals(progress);
    
    updateVisuals(elapsed);
    
    // Continue animation
    animationState.animationId = requestAnimationFrame(animate);
  }}

  function resetSimulation() {{
    // Stop animation
    animationState.isRunning = false;
    if (animationState.animationId) {{
      cancelAnimationFrame(animationState.animationId);
    }}
    
    animationState.startTime = 0;
    
    // Reset UI
    const startBtn = document.getElementById('startBtn');
    const statusDisplay = document.getElementById('statusDisplay');
    
    startBtn.disabled = false;
    startBtn.textContent = '▶ Start Animation';
    statusDisplay.textContent = 'Ready to Start';
    statusDisplay.className = 'status ready';
    
    // Reset sliders to default (optional)
    // document.getElementById('slider1').value = defaultValue1;
    // document.getElementById('slider2').value = defaultValue2;
    
    // Reset visuals to initial state
    updateSimulation();
  }}

  // === SLIDER HANDLERS ===
  function handleSlider1Change(e) {{
    const value = parseFloat(e.target.value);
    document.getElementById('slider1Val').textContent = value + ' [unit]';
    updateSimulation();
  }}

  function handleSlider2Change(e) {{
    const value = parseFloat(e.target.value);
    document.getElementById('slider2Val').textContent = value + ' [unit]';
    updateSimulation();
  }}

  // === VISUAL UPDATES ===
  function updateSimulation() {{
    // Read current slider values
    const value1 = parseFloat(document.getElementById('slider1').value);
    const value2 = parseFloat(document.getElementById('slider2').value);
    
    // Update stats
    // document.getElementById('stat1').textContent = calculatedValue1;
    
    // If not animating, update static visual
    if (!animationState.isRunning) {{
      updateVisuals(0);
    }}
  }}

  function updateVisuals(timeOrProgress) {{
    // === UPDATE SVG ELEMENTS ===
    // Use setAttribute to modify SVG attributes
    // Examples:
    // element.setAttribute('cx', newX);
    // element.setAttribute('fill', newColor);
    // element.setAttribute('transform', `translate(${{x}},${{y}})`);
    
    // For animations, use timeOrProgress to calculate positions
  }}

  // === START ON LOAD ===
  document.addEventListener('DOMContentLoaded', initSimulation);
</script>

</body>
</html>

=== YOUR PLAN ===
{plan}

=== CONCEPT DATA ===
{spec_json}

=== CRITICAL REQUIREMENTS ===
1. SVG MUST have id="simCanvas"
2. Buttons MUST have id="startBtn" and id="resetBtn"
3. At least 2 sliders with proper event handlers
4. Animation MUST use requestAnimationFrame
5. Animation MUST be VISIBLE and CONTINUOUS (not just one-time update)
6. Reset MUST stop animation and return to initial state
7. All values MUST have units displayed

Generate ONLY complete HTML. No explanations."""
    )

    return prompt | llm


# ------------ Step 3: Bug-fix chain ------------

def build_bugfix_chain():
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash-lite",
        temperature=0.2,
        api_key=os.getenv("GOOGLE_API_KEY_BUGFIX"),
    )

    prompt = ChatPromptTemplate.from_template(
        """Fix critical issues in this simulation HTML.

CRITICAL CHECKS:
1. id="simCanvas" exists
2. id="startBtn" exists with click handler
3. id="resetBtn" exists with click handler
4. At least 2 sliders with input event listeners
5. requestAnimationFrame used for animation
6. cancelAnimationFrame called on reset
7. Button states managed correctly
8. No undefined variables
9. Viewport meta tag present

RESPOND with JSON:
{{
  "has_bug": true/false,
  "notes": "Brief fixes description",
  "html": "Complete fixed HTML"
}}

HTML:
{html}"""
    )

    return prompt | llm


# ------------ Step 4: Student Feedback chain ------------

def build_student_feedback_chain():
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash-lite",
        temperature=0.5,
        api_key=os.getenv("GOOGLE_API_KEY_BUGFIX")
    )

    prompt = ChatPromptTemplate.from_template(
        """Test this simulation as a student. Focus on animation quality.

EVALUATE:
1. Does Start button trigger VISIBLE, CONTINUOUS animation?
2. Does Reset stop animation and reset everything?
3. Is the concept clearly demonstrated visually?
4. Do sliders work in real-time?
5. Is it engaging?

RESPOND with JSON:
{{
  "first_impressions": ["Animation quality", "Concept clarity"],
  "visual": ["What animates well", "What needs improvement"],
  "controls": ["Button functionality", "Slider responsiveness"],
  "explanations": ["Text clarity", "Learning value"],
  "bugs_or_issues": ["Specific issues" or "None found"],
  "suggestions": ["Concrete improvements"]
}}

ONE sentence per point.

HTML:
{html}"""
    )

    return prompt | llm


# ------------ Step 5: Incorporate Feedback chain ------------

def build_incorporate_feedback_chain():
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash-lite",
        temperature=0.2,
        api_key=os.getenv("GOOGLE_API_KEY_BUGFIX")
    )

    prompt = ChatPromptTemplate.from_template(
        """Improve simulation based on feedback.

ALLOWED:
✓ Enhance animation smoothness
✓ Improve visual feedback
✓ Better button states
✓ Add status indicators
✓ Improve colors/contrast
✓ Add units to displays

FORBIDDEN:
✗ Break animations
✗ Remove Start/Reset
✗ Remove sliders

Feedback:
{feedback_json}

HTML:
{html}

Return ONLY improved HTML."""
    )

    return prompt | llm


# ------------ Step 6: Review chain ------------

def build_review_chain():
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash-lite",
        temperature=0.1,
        api_key=os.getenv("GOOGLE_API_KEY_BUGFIX")
    )

    prompt = ChatPromptTemplate.from_template(
        """Final review for student readiness.

MUST HAVE:
✓ Valid HTML5
✓ Viewport meta tag
✓ SVG id="simCanvas"
✓ Start button (id="startBtn") - triggers animation
✓ Reset button (id="resetBtn") - stops and resets
✓ 2+ working sliders
✓ updateSimulation() function
✓ initSimulation() function
✓ DOMContentLoaded listener
✓ requestAnimationFrame for animation
✓ cancelAnimationFrame on reset
✓ Clear visual concept demonstration
✓ Button state management

RESPOND with JSON:
{{
  "approved": true/false,
  "reasons": "Specific reason"
}}

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
    print("MOBILE-FIRST SIMULATION GENERATION PIPELINE")
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

    # 2. Build chains once
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