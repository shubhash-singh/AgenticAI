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
from langchain_openai import ChatOpenAI

# orchestrator import
from sim_generator import generate_simulation_with_checks

load_dotenv()  # load .env

def make_chain(prompt_template: str, llm_instance):
    prompt = ChatPromptTemplate.from_template(prompt_template)
    return prompt | llm_instance


def build_all_chains():

    base_url = "https://openrouter.ai/api/v1"

    planner_llm = ChatOpenAI(
        model="kwaipilot/kat-coder-pro:free",
        temperature=0.3,
        api_key=os.getenv("OPENROUTER_API_KEY"),
        base_url=base_url,
    )

    creation_llm = ChatOpenAI(
        model="kwaipilot/kat-coder-pro:free",
        temperature=0,
        api_key=os.getenv("OPENROUTER_API_KEY"),
        base_url=base_url,
    )

    bugfix_llm = ChatOpenAI(
        model="kwaipilot/kat-coder-pro:free",
        temperature=0.2,
        api_key=os.getenv("OPENROUTER_API_KEY"),
        base_url=base_url,
    )

    student_interaction_llm = ChatOpenAI(
        model="kwaipilot/kat-coder-pro:free",
        temperature=0.6,
        api_key=os.getenv("OPENROUTER_API_KEY"),
        base_url=base_url,
    )

    incorporate_feedback_llm = ChatOpenAI(
        model="kwaipilot/kat-coder-pro:free",
        temperature=0.2,
        api_key=os.getenv("OPENROUTER_API_KEY"),
        base_url=base_url,
    )

    review_llm = ChatOpenAI(
        model="kwaipilot/kat-coder-pro:free",
        temperature=0.1,
        api_key=os.getenv("OPENROUTER_API_KEY"),
        base_url=base_url,
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

    creation_prompt = """
You are an expert HTML Simulation Generator specializing in visual, interactive educational content.

INPUTS:
Blueprint: {plan}

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

OUTPUT RULES:
- Output ONLY valid JSON with the structure above
- NO markdown code blocks (```)
- NO commentary or explanations
- The ENTIRE HTML must be a single string value for "index.html"
- Escape all quotes inside the HTML: use \" for quotes inside the string
- No newlines in the JSON (they can be in the HTML string with \\n)
"""

    bugfix_prompt = """
You are a Senior HTML/CSS/JS Debugger specializing in mobile-responsive simulations.

INPUT HTML:
{html}

SYSTEMATIC BUG-FIX CHECKLIST:

1. STRUCTURAL FIXES:
   ✓ Ensure <!DOCTYPE html> is present
   ✓ Add viewport meta tag if missing
   ✓ Validate all HTML tags are properly closed
   ✓ Check for proper nesting (no overlapping tags)

2. LAYOUT FIXES (HIGHEST PRIORITY):
   ✓ Verify #visual-area has explicit height (vh/px)
   ✓ Ensure visual elements are centered using flexbox
   ✓ Check all absolute positions have proper parent context
   ✓ Validate responsive units (avoid fixed px for widths)
   ✓ Fix any overflow issues
   
3. POSITIONING CORRECTIONS:
   - If SVG is not centered, wrap in flex container:
     <div style="display: flex; justify-content: center; align-items: center; height: 100%;">
       <svg>...</svg>
     </div>
   - If canvas is misaligned, add explicit sizing and centering
   - If elements overlap, adjust z-index and positioning

4. MOBILE RESPONSIVENESS:
   ✓ All touch targets ≥ 48px
   ✓ Font sizes ≥ 16px (14px minimum for labels)
   ✓ Container max-width with proper margins
   ✓ No horizontal scrolling on 360px width

5. JAVASCRIPT FIXES:
   ✓ All event listeners properly attached
   ✓ No undefined variables or functions
   ✓ Add null checks before DOM manipulation
   ✓ Wrap code in DOMContentLoaded if needed

6. VISUAL ENHANCEMENTS:
   ✓ Add smooth transitions where missing
   ✓ Ensure proper contrast ratios
   ✓ Add loading states if applicable
   ✓ Fix any color/visibility issues

7. CODE QUALITY:
   ✓ Remove console.logs
   ✓ Fix any syntax errors
   ✓ Ensure proper indentation
   ✓ Add comments for complex logic

COMMON FIXES TO APPLY:

Layout Centering Fix:
```css
#visual-area {{
    display: flex;
    justify-content: center;
    align-items: center;
    height: 50vh;
    min-height: 300px;
}}
```

SVG Responsive Fix:
```html
<svg viewBox="0 0 400 400" style="width: 90%; max-width: 400px; height: auto;">
```

Touch Target Fix:
```css
input[type="range"], button {{
    min-height: 48px;
    min-width: 48px;
}}
```

OUTPUT FORMAT:
{{
  "fixed": true,
  "index.html": "<!DOCTYPE html>...[CORRECTED HTML]...",
  "explanations": [
    "Fixed visual centering by adding flexbox to #visual-area",
    "Added viewport meta tag for mobile responsiveness",
    "Corrected SVG sizing with viewBox and percentage width",
    "Increased button touch targets to 48px minimum"
  ]
}}

CRITICAL RULES:
- Output ONLY valid JSON
- NO markdown code blocks
- Provide complete corrected HTML
- List all fixes made in explanations array
"""

    student_interaction_prompt = """
You are an Educational Content Designer for CBSE Class 7 students.

INPUTS:
Spec: {spec_json}
Blueprint: {plan}

Create engaging, age-appropriate questions that test conceptual understanding.

QUESTION DESIGN PRINCIPLES:
1. Progressive Difficulty:
   - Q1: Observation (what do you see?)
   - Q2: Prediction (what will happen if?)
   - Q3: Application (how would you use this?)

2. Question Quality:
   - Clear, unambiguous wording
   - Based on simulation interactions
   - Test understanding, not memorization
   - Avoid trick questions

3. MCQ Requirements:
   - 4 options (A, B, C, D)
   - One clearly correct answer
   - Plausible distractors (common misconceptions)
   - Options of similar length

4. Hints:
   - Guide thinking without revealing answer
   - Encourage experimentation
   - Reference simulation controls

OUTPUT FORMAT:
{{
  "intro": "Friendly 2-3 sentence introduction encouraging exploration",
  "questions": [
    {{
      "question": "Clear question based on simulation (end with ?)",
      "type": "mcq",
      "options": [
        "A) First option",
        "B) Second option",
        "C) Third option",
        "D) Fourth option"
      ],
      "correct_index": 0,
      "hint": "Guiding hint without revealing answer",
      "explanation": "Why this answer is correct (revealed after answering)"
    }},
    {{
      "question": "What would happen if you increased [variable] to maximum?",
      "type": "mcq",
      "options": ["A) ...", "B) ...", "C) ...", "D) ..."],
      "correct_index": 2,
      "hint": "Try adjusting the slider and observe the changes",
      "explanation": "Explanation of the concept"
    }},
    {{
      "question": "In real life, where would you see this concept?",
      "type": "mcq",
      "options": ["A) ...", "B) ...", "C) ...", "D) ..."],
      "correct_index": 1,
      "hint": "Think about everyday situations",
      "explanation": "Real-world application explanation"
    }}
  ],
  "followups": [
    "Try setting both variables to maximum. What do you notice?",
    "Can you find a combination that creates the most interesting result?",
    "Challenge: Predict the outcome before making changes"
  ],
  "summary": "Brief recap of key learning points (2-3 sentences)"
}}

TONE GUIDELINES:
- Encouraging and supportive
- Age-appropriate vocabulary (7th grade level)
- Conversational but educational
- Avoid condescension

CRITICAL RULES:
- Output ONLY valid JSON
- NO markdown code blocks
- Exactly 3 questions
- All questions must be MCQ type
- correct_index must be 0, 1, 2, or 3
"""

    incorporate_feedback_prompt = """
You are a Simulation Improvement Specialist.

INPUTS:
Current HTML: {html}
Feedback: {feedback_text}

Your task: Apply the requested improvements while maintaining quality and constraints.

IMPROVEMENT PROCESS:
1. Parse Feedback:
   - Identify specific issues mentioned
   - Prioritize by impact (critical > major > minor)
   - Note any conflicting requests

2. Apply Changes:
   - Make targeted modifications
   - Preserve working functionality
   - Maintain mobile-first design
   - Keep file self-contained

3. Verify Quality:
   - Test that changes don't break existing features
   - Ensure mobile responsiveness remains intact
   - Check that visuals still align properly

COMMON FEEDBACK TYPES & RESPONSES:

"Colors are not good":
- Update color scheme to higher contrast
- Ensure WCAG AA compliance (4.5:1 ratio)
- Use complementary colors from color theory

"Animations are too fast/slow":
- Adjust transition duration (typical: 300-500ms)
- Add easing functions (ease-in-out)

"Controls are hard to use":
- Increase touch target sizes
- Add more spacing
- Make labels clearer

"Visual is not clear":
- Increase size of main visual
- Add labels or legends
- Improve contrast

"Need more interactivity":
- Add hover effects
- Add feedback animations
- Add sound indicators (optional)

OUTPUT FORMAT:
{{
  "index.html": "<!DOCTYPE html>...[IMPROVED HTML]...",
  "changes_made": [
    "Increased slider touch targets from 40px to 52px",
    "Changed color scheme to higher contrast (#333 on #fff)",
    "Added smooth transitions to all visual elements (300ms ease)",
    "Improved centering of main SVG graphic"
  ]
}}

RULES:
- Output ONLY valid JSON
- NO markdown code blocks
- Provide complete updated HTML
- Document every change made
- Maintain all existing functionality
"""

    review_prompt = """
You are a Senior Quality Assurance Specialist for educational simulations.

INPUT HTML:
{html}

Conduct a comprehensive quality review using CBSE Class 7 standards.

EVALUATION CRITERIA:

1. PEDAGOGICAL CLARITY (0-5):
   5: Crystal clear learning objectives, perfect for target age
   4: Very clear with minor ambiguity
   3: Acceptable clarity, some improvements needed
   2: Unclear objectives or confusing presentation
   1: Poor pedagogical design
   0: No clear educational value

   Check:
   - Are learning objectives evident?
   - Is information presented at 7th grade level?
   - Are instructions clear and concise?
   - Is the concept well explained visually?

2. CONCEPTUAL CORRECTNESS (0-5):
   5: 100% scientifically accurate, no misconceptions
   4: Accurate with very minor simplifications
   3: Mostly accurate, acceptable simplifications
   2: Some inaccuracies present
   1: Major scientific errors
   0: Fundamentally incorrect

   Check:
   - Scientific/mathematical accuracy
   - Appropriate simplification for age group
   - No perpetuation of misconceptions
   - Correct use of units and terminology

3. MOBILE RESPONSIVENESS (0-5):
   5: Perfect mobile experience, all elements accessible
   4: Very good with minor layout issues
   3: Functional but needs improvements
   2: Significant mobile usability issues
   1: Barely usable on mobile
   0: Broken on mobile

   Check:
   - Viewport meta tag present
   - All elements visible on 360px width
   - Touch targets ≥ 48px
   - No horizontal scrolling
   - Proper text sizing (≥ 16px)
   - Visual elements properly positioned and centered

4. INTERACTIVITY QUALITY (0-5):
   5: Highly engaging, immediate feedback, smooth animations
   4: Very interactive with minor lag
   3: Acceptable interactivity
   2: Limited or clunky interactions
   1: Barely interactive
   0: No meaningful interactivity

   Check:
   - Controls respond immediately (< 100ms)
   - Visual feedback for all interactions
   - Smooth animations (no jank)
   - Intuitive control placement
   - Engaging user experience

5. CODE RELIABILITY (0-5):
   5: Production-ready, error-free, well-structured
   4: Very good with minor optimization opportunities
   3: Functional with some code quality issues
   2: Works but has errors or poor structure
   1: Frequent errors or crashes
   0: Non-functional code

   Check:
   - No JavaScript errors
   - Proper event handling
   - Error handling present
   - Clean, maintainable code
   - Self-contained (no external dependencies)

6. SAFETY & AGE APPROPRIATENESS (0-5):
   5: Perfectly safe and age-appropriate
   4: Very appropriate with minor considerations
   3: Acceptable with some concerns
   2: Some inappropriate content
   1: Multiple safety/appropriateness issues
   0: Unsafe or highly inappropriate

   Check:
   - Content suitable for 12-13 year olds
   - No dangerous demonstrations
   - Appropriate language and themes
   - No external links or resources

PASSING CRITERIA:
- ALL scores must be ≥ 3
- Average score must be ≥ 4.0
- No critical safety issues

OUTPUT FORMAT:
{{
  "scores": {{
    "pedagogical_clarity": 4,
    "conceptual_correctness": 5,
    "mobile_responsiveness": 3,
    "interactivity_quality": 4,
    "code_reliability": 4,
    "safety_age_appropriateness": 5
  }},
  "average_score": 4.2,
  "pass": true,
  "strengths": [
    "Excellent visual representation of concept",
    "Very smooth and responsive controls",
    "Scientifically accurate throughout"
  ],
  "required_changes": [
    "Increase touch target size for reset button to 48px",
    "Add more spacing between control elements (currently 4px, should be 8px)",
    "Center the main SVG graphic properly using flexbox"
  ],
  "optional_improvements": [
    "Consider adding sound feedback for interactions",
    "Could add more color contrast for better visibility"
  ],
  "return_to": "bugfix"
}}

return_to options:
- "none": Approved, no changes needed
- "bugfix": Minor technical fixes required
- "creation": Major redesign needed
- "planner": Fundamental concept issues

RULES:
- Output ONLY valid JSON
- NO markdown code blocks
- Be strict but fair in evaluation
- Provide actionable feedback
- Focus on student learning experience
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