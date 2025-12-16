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

# imports for langchain-style chains
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

# orchestrator import
from sim_generator import generate_simulation

load_dotenv()  # load .env

def make_chain(prompt_template: str, llm_instance):
    """Create a chain from prompt template and LLM"""
    prompt = ChatPromptTemplate.from_template(prompt_template)
    return prompt | llm_instance


def build_chains():
    """Build the three agent chains"""
    
    base_url = "https://openrouter.ai/api/v1"

    planner_llm = ChatOpenAI(
        model="kwaipilot/kat-coder-pro:free",
        temperature=0,
        api_key=os.getenv("OPENROUTER_API_KEY"),
        base_url=base_url
    )

    creator_llm = ChatOpenAI(
        model="kwaipilot/kat-coder-pro:free",
        temperature=0,
        api_key=os.getenv("OPENROUTER_API_KEY"),
        base_url=base_url
    )

    reviewer_llm = ChatOpenAI(
        model="kwaipilot/kat-coder-pro:free",
        temperature=0,
        api_key=os.getenv("OPENROUTER_API_KEY"),
        base_url=base_url
    )


    planner_prompt = """
You are an expert Simulation Planner for CBSE Class 7 students.

Input spec.json:
{spec_json}

Create a detailed, pedagogically sound blueprint that prioritizes VISUAL LEARNING over text.

CRITICAL REQUIREMENTS:
1. Visual-First Approach:
   - Plan specific visual elements (shapes, colors, animations)
   - Minimize text to essential labels only
   - Use visual metaphors students can understand
   - Plan smooth animations for state changes

2. Mobile Layout Planning:
   - Single column, vertical scroll
   - Clear visual hierarchy (header → visual area → controls → info)
   - All elements must fit within 360px width minimum
   - Touch targets ≥ 48px with 8px spacing

3. Variable Limits:
   - Maximum 3 controllable variables (complexity management)
   - Each variable must have clear visual feedback
   - Use intuitive ranges (0-100, 1-10, etc.)

4. Interaction Design:
   - Specify exact control types (slider/button/toggle)
   - Define what changes visually when each control is used
   - Plan immediate visual feedback (< 100ms response)

OUTPUT STRUCTURE (MUST BE VALID JSON ONLY):
{{
  "learning_objectives": [
    "Clear, measurable objective 1",
    "Clear, measurable objective 2",
    "Clear, measurable objective 3"
  ],
  "key_concepts": [
    "Main concept",
    "Supporting concept 1",
    "Supporting concept 2"
  ],
  "visual_design": {{
    "main_display": "Specific description of central visual (e.g., 'SVG circle that changes color and size')",
    "color_scheme": ["#primary", "#secondary", "#accent"],
    "animation_style": "smooth/stepped/continuous",
    "visual_metaphor": "Real-world analogy for the concept"
  }},
  "variables_to_simulate": [
    {{
      "name": "Variable1",
      "control_type": "slider",
      "min": 0,
      "max": 100,
      "default": 50,
      "unit": "unit",
      "visual_effect": "Specific visual change (e.g., 'changes circle radius from 20px to 200px')"
    }}
  ],
  "layout_structure": {{
    "sections": [
      {{"id": "header", "height": "60px", "content": "Title and brief description"}},
      {{"id": "visual-area", "height": "50vh", "content": "Main interactive visualization"}},
      {{"id": "controls", "height": "auto", "content": "Sliders and buttons"}},
      {{"id": "info", "height": "auto", "content": "Current values and observations"}}
    ],
    "spacing": "16px between sections"
  }},
  "simulation_logic": [
    "Step 1: Initialize visual with default values",
    "Step 2: When slider moves, calculate new value",
    "Step 3: Animate visual change over 300ms",
    "Step 4: Update display text with new values"
  ],
  "text_instructions": "One sentence explanation (max 15 words)",
  "misconceptions_to_address": ["Common misconception 1", "Common misconception 2"],
  "safety_constraints": ["Age-appropriate content", "No external resources"]
}}

CRITICAL OUTPUT RULES:
- Output ONLY the JSON object above
- NO markdown code blocks (```), NO extra text
- ALL fields must be present
- Ensure valid JSON syntax (proper quotes, commas, brackets)
"""

    creator_prompt = """
You are an expert HTML Simulation Generator specializing in visual, interactive educational content.

INPUTS:

1) DEVELOPMENT PLAN (verbatim planner output):
{development_plan}

2) STRUCTURED BLUEPRINT (authoritative JSON):
{blueprint}


YOUR MISSION: Create a COMPLETE, SELF-CONTAINED, MOBILE-FIRST HTML simulation that works perfectly on small screens.

CRITICAL LAYOUT REQUIREMENTS:
1. Container Structure:
   ```
   <div id="app" style="max-width: 600px; margin: 0 auto; padding: 16px;">
     <header>...</header>
     <div id="visual-area" style="position: relative; height: 50vh; background: #f5f5f5;">
       <!-- ALL VISUALS HERE WITH EXPLICIT POSITIONING -->
     </div>
     <div id="controls">...</div>
     <div id="info">...</div>
   </div>
   ```

2. Visual Element Positioning (CRITICAL):
   - Use CSS Flexbox or Grid for predictable layouts
   - Center visuals with: `display: flex; justify-content: center; align-items: center;`
   - For SVG: Set explicit viewBox and use percentages for responsive sizing
   - For Canvas: Set explicit width/height and use CSS to scale
   - NEVER use absolute positioning without clear parent context
   - Example SVG centering:
     ```
     <div style="display: flex; justify-content: center; align-items: center; height: 100%;">
       <svg viewBox="0 0 400 400" style="width: 90%; max-width: 400px; height: auto;">
         <!-- shapes here -->
       </svg>
     </div>
     ```

3. Responsive Design:
   - All sizes in vh/vw/% or with max-width constraints
   - Font size: minimum 16px (14px for captions)
   - Touch targets: minimum 48px × 48px
   - Spacing: 16px between major sections, 8px between controls

4. Visual Requirements:
   - Use SVG for shapes and graphics (NOT images)
   - Implement smooth CSS transitions (transition: all 0.3s ease)
   - Show visual feedback for ALL interactions
   - Use contrasting colors (#333 text on #fff background minimum)
   - Add visual labels/legends where needed

5. Control Specifications:
   - Sliders: `<input type="range" style="width: 100%; height: 44px;">`
   - Buttons: `style="min-height: 48px; padding: 12px 24px; font-size: 16px;"`
   - Display values next to controls in real-time

6. JavaScript Requirements:
   - Use event listeners (addEventListener) not inline handlers
   - Update visuals immediately on input
   - Add smooth animations with requestAnimationFrame for complex updates
   - Include error handling (try-catch blocks)
   - Example structure:
     ```javascript
     const slider = document.getElementById('slider1');
     const visual = document.getElementById('main-visual');
     
     slider.addEventListener('input', (e) => {{
       const value = e.target.value;
       updateVisual(value);
       updateDisplay(value);
     }});
     
     function updateVisual(value) {{
       // Smooth visual updates
       const scale = value / 50;
       visual.style.transform = 'scale(' + scale + ')';
     }}
     ```

7. Performance:
   - Debounce rapid updates if needed
   - Use CSS transforms (not top/left) for animations
   - Keep JavaScript minimal and efficient

MANDATORY HTML STRUCTURE:
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>[Concept Name] - Interactive Simulation</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            line-height: 1.6;
            color: #333;
            background: #f9f9f9;
        }}
        #app {{ 
            max-width: 600px; 
            margin: 0 auto; 
            padding: 16px; 
            background: white;
            min-height: 100vh;
        }}
        header {{
            padding: 16px 0;
            text-align: center;
            border-bottom: 2px solid #e0e0e0;
        }}
        h1 {{ font-size: 24px; margin-bottom: 8px; }}
        .subtitle {{ font-size: 14px; color: #666; }}
        
        #visual-area {{
            position: relative;
            height: 50vh;
            min-height: 300px;
            background: #f5f5f5;
            border-radius: 8px;
            margin: 16px 0;
            display: flex;
            justify-content: center;
            align-items: center;
            overflow: hidden;
        }}
        
        #controls {{
            padding: 16px;
            background: #fafafa;
            border-radius: 8px;
            margin: 16px 0;
        }}
        
        .control-group {{
            margin: 16px 0;
        }}
        
        .control-label {{
            display: flex;
            justify-content: space-between;
            margin-bottom: 8px;
            font-weight: 500;
        }}
        
        input[type="range"] {{
            width: 100%;
            height: 44px;
            cursor: pointer;
        }}
        
        button {{
            width: 100%;
            min-height: 48px;
            padding: 12px;
            font-size: 16px;
            background: #4CAF50;
            color: white;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            margin: 8px 0;
        }}
        
        button:active {{
            transform: scale(0.98);
        }}
        
        #info {{
            padding: 16px;
            background: #e3f2fd;
            border-radius: 8px;
            margin: 16px 0;
        }}
        
        /* Add your specific visual styles here */
    </style>
</head>
<body>
    <div id="app">
        <header>
            <h1>[Your Title]</h1>
            <p class="subtitle">[One line description]</p>
        </header>
        
        <div id="visual-area">
            <!-- Your SVG/Canvas visualization here with proper centering -->
        </div>
        
        <div id="controls">
            <!-- Your controls here -->
        </div>
        
        <div id="info">
            <!-- Current values and observations -->
        </div>
    </div>
    
    <script>
        // Your JavaScript here
        // Follow the blueprint's simulation_logic exactly
    </script>
</body>
</html>

CRITICAL OUTPUT FORMAT:
{{
  "index.html": "<!DOCTYPE html>...[COMPLETE HTML AS SINGLE STRING WITH ESCAPED QUOTES]..."
}}

AUTHORITATIVE RULES (MANDATORY):

- The DEVELOPMENT PLAN explains INTENT and DESIGN RATIONALE.
- The STRUCTURED BLUEPRINT defines REQUIRED FEATURES.

You MUST:
- Implement EVERY learning objective
- Implement EVERY variable
- Implement EVERY interaction described
- Implement ALL visual metaphors and animations
- Follow simulation_logic step-by-step

You MUST NOT:
- Invent new variables
- Skip any planner concept
- Replace planner intent with your own design

If something in the development plan is ambiguous,
use the STRUCTURED BLUEPRINT as the source of truth.

Before generating HTML, internally verify:
- Every blueprint key is implemented
- Every variable has a control and visual feedback
- Every simulation_logic step maps to JS code

If any item is missing, STOP and regenerate.


OUTPUT RULES:
- Output ONLY valid JSON with the structure above
- NO markdown code blocks (```)
- NO commentary or explanations
- The ENTIRE HTML must be a single string value for "index.html"
- Escape all quotes inside the HTML: use \" for quotes inside the string
- No newlines in the JSON (they can be in the HTML string with \\n)
"""

    reviewer_prompt = """
You are a Quality Assurance Specialist for educational simulations.

INPUTS:
HTML Simulation: {html}
Blueprint (Plan): {plan}

Your task: Review the simulation against the blueprint and quality standards.

EVALUATION CRITERIA (Score 0-5 for each):

1. BLUEPRINT ADHERENCE (0-5):
   - Are all planned variables implemented?
   - Does visual design match the blueprint?
   - Are learning objectives achievable?
   - Is simulation logic correct?
   
2. PEDAGOGICAL CLARITY (0-5):
   - Clear learning objectives?
   - Age-appropriate (Class 7)?
   - Instructions clear?
   - Concept well-explained?

3. CONCEPTUAL CORRECTNESS (0-5):
   - Scientifically accurate?
   - Appropriate simplifications?
   - No misconceptions?
   - Correct terminology?

4. MOBILE RESPONSIVENESS (0-5):
   - Viewport meta tag present?
   - Works on 360px width?
   - Touch targets ≥ 48px?
   - No horizontal scroll?
   - Visual elements centered?

5. INTERACTIVITY QUALITY (0-5):
   - Controls respond immediately?
   - Visual feedback present?
   - Smooth animations?
   - Engaging experience?

6. CODE QUALITY (0-5):
   - No JavaScript errors?
   - Proper event handling?
   - Clean structure?
   - Self-contained?

PASSING CRITERIA:
- ALL scores ≥ 3
- Average score ≥ 4.0
- Blueprint requirements met

OUTPUT FORMAT:
{{
  "scores": {{
    "blueprint_adherence": 4,
    "pedagogical_clarity": 4,
    "conceptual_correctness": 5,
    "mobile_responsiveness": 3,
    "interactivity_quality": 4,
    "code_quality": 4
  }},
  "average_score": 4.0,
  "pass": true,
  "strengths": [
    "Excellent visual representation",
    "All blueprint features implemented"
  ],
  "required_changes": [
    "Increase button touch targets to 48px"
  ],
  "blueprint_compliance": {{
    "all_variables_present": true,
    "visual_design_matches": true,
    "logic_correct": true,
    "missing_features": []
  }}
}}

RULES:
- Output ONLY valid JSON
- NO markdown code blocks
- Be strict about blueprint compliance
- Provide actionable feedback
"""

    # Create chains
    planner_chain = make_chain(planner_prompt, planner_llm)
    creator_chain = make_chain(creator_prompt, creator_llm)
    reviewer_chain = make_chain(reviewer_prompt, reviewer_llm)

    # Return chains and prompt strings for export
    prompts = {
        "planner": planner_prompt,
        "creator": creator_prompt,
        "reviewer": reviewer_prompt
    }
    
    return planner_chain, creator_chain, reviewer_chain, prompts


def main():
    parser = argparse.ArgumentParser(
        description="Generate CBSE Class 7 simulation using LangGraph"
    )
    parser.add_argument(
        "--spec", "-s", 
        type=str, 
        default="src_lang_graph/spec.json",
        help="Path to spec JSON file"
    )
    parser.add_argument(
        "--output-root", 
        type=str, 
        default="langGraph_output",
        help="Root directory for outputs"
    )
    parser.add_argument(
        "--max-iterations",
        type=int,
        default=1,
        help="Maximum revision iterations"
    )
    args = parser.parse_args()

    # Validate spec exists
    if not Path(args.spec).exists():
        print(f"❌ Spec not found: {args.spec}")
        return

    print("Initializing LLM agents...")
    planner_chain, creator_chain, reviewer_chain, prompts = build_chains()
    print("✓ Agents ready\n")

    # Run generation
    approved, html, output_folder = generate_simulation(
        spec_path=args.spec,
        planner_chain=planner_chain,
        creator_chain=creator_chain,
        reviewer_chain=reviewer_chain,
        output_root=args.output_root,
        max_iterations=args.max_iterations,
        prompts=prompts  # Pass prompts for export
    )

    # Final summary
    print("\n" + "=" * 70)
    if approved:
        print("✅ Simulation APPROVED and ready!")
    else:
        print("⚠️  Simulation generated but needs revision")
    print("=" * 70)
    print(f"📁 Outputs: {output_folder}")
    print(f"📄 Main file: {output_folder / '4_final_output.html'}")
    print(f"\n💡 Open the HTML file in a browser to view the simulation\n")


if __name__ == "__main__":
    main()