# Complete Flow Documentation: CBSE Class 7 Simulation Generator

## Overview

This system is an agentic AI pipeline that generates interactive HTML simulations for CBSE Class 7 students. It uses a multi-agent architecture where each agent (node) performs a specific task in the simulation generation process.

---

## System Architecture

The system consists of **6 main nodes** (agents) that work sequentially:

1. **Planner Node** - Creates a blueprint/plan
2. **Creator Node** - Generates the HTML simulation
3. **Bugfix Node** - Fixes structural and code issues
4. **Student Interaction Node** - Generates questions and feedback
5. **Incorporate Feedback Node** - (Optional) Applies improvements
6. **Review Node** - Evaluates and scores the final output

---

## Complete Data Flow

```
INPUT: spec.json
    ↓
[1] PLANNER NODE
    Input: spec.json
    Output: Blueprint JSON
    ↓
[2] CREATOR NODE
    Input: spec.json + Blueprint JSON
    Output: HTML file (index.html)
    ↓
[3] BUGFIX NODE
    Input: HTML from Creator
    Output: Fixed HTML
    ↓
[4] STUDENT INTERACTION NODE (Parallel)
    Input: spec.json + Blueprint JSON
    Output: Questions JSON
    ↓
[5] REVIEW NODE
    Input: Fixed HTML
    Output: Review scores + Pass/Fail
    ↓
OUTPUT: Final HTML + All intermediate files
```

---

## Detailed Node-by-Node Breakdown

### Node 1: PLANNER NODE

**Purpose**: Converts the learning concept into a detailed simulation blueprint.

**Input**:
- `spec.json` - The original concept specification containing:
  - Concept name
  - Description
  - Key topics
  - Working principles
  - Real-life applications
  - Questions

**Processing**:
- LLM Agent: `ChatGoogleGenerativeAI` (gemini-2.5-flash-lite) or OpenRouter model
- Temperature: 0.3
- Analyzes the concept and creates a structured plan

**Output**:
- **File**: `1_planner_blueprint.json`
- **Content**: JSON blueprint containing:
  ```json
  {
    "learning_objectives": [...],
    "key_concepts": [...],
    "variables_to_simulate": [...],
    "user_interactions": {...},
    "simulation_logic": [...],
    "mobile_ui_plan": {...},
    "misconceptions_to_address": [...],
    "text_instructions_for_students": "...",
    "file_target": "single_file_html",
    "safety_constraints": [...]
  }
  ```

**Additional Files Saved**:
- `1_planner_raw_response.txt` - Raw LLM response before parsing

**Where Output Goes**:
- → **Creator Node** (as `plan` parameter)
- → **Student Interaction Node** (as `plan` parameter)
- → Saved to output directory for debugging

---

### Node 2: CREATOR NODE

**Purpose**: Generates the actual HTML simulation file based on the blueprint.

**Input**:
- `spec.json` - Original concept specification
- `plan` (Blueprint JSON) - From Planner Node

**Processing**:
- LLM Agent: `ChatGoogleGenerativeAI` (gemini-2.5-flash-lite) or OpenRouter model
- Temperature: 0.2
- Creates a complete, self-contained HTML file with:
  - Inline CSS styles
  - Inline JavaScript
  - Interactive controls (sliders, buttons)
  - Visual simulation area
  - Mobile-responsive design

**Output**:
- **File**: `2_creator_output.html`
- **Content**: Complete HTML file with:
  - DOCTYPE and HTML structure
  - Viewport meta tag
  - Embedded CSS in `<style>` tag
  - Embedded JavaScript in `<script>` tag
  - Interactive simulation elements
  - 7th-grade reading level text

**Additional Files Saved**:
- `2_creator_raw_response.txt` - Raw LLM response (may contain JSON wrapper or raw HTML)

**Where Output Goes**:
- → **Bugfix Node** (as `html` parameter)
- → Saved to output directory

**Validation**:
- Checks for minimum requirements:
  - DOCTYPE declaration
  - Viewport meta tag
  - Interactive controls
  - Styling present

---

### Node 3: BUGFIX NODE

**Purpose**: Fixes structural errors, broken references, and code issues in the HTML.

**Input**:
- `html` - HTML file from Creator Node

**Processing**:
- LLM Agent: `ChatGoogleGenerativeAI` (gemini-2.5-flash-lite) or OpenRouter model
- Temperature: 0.2
- Fixes:
  - Structural HTML errors
  - Broken DOM references
  - Missing IDs
  - ARIA attributes for accessibility
  - Mobile responsiveness issues
  - JavaScript syntax errors
  - Missing viewport meta tag
  - Touch target sizes (ensures ≥ 44px)

**Output**:
- **File**: `3_bugfix_output.html`
- **Content**: Corrected HTML file
- **Format**: JSON response containing:
  ```json
  {
    "fixed": true/false,
    "index.html": "<!DOCTYPE html>...",
    "explanations": ["fix 1", "fix 2", ...]
  }
  ```

**Additional Files Saved**:
- `3_bugfix_raw_response.txt` - Raw LLM response

**Where Output Goes**:
- → **Review Node** (as `html` parameter)
- → **Final Output** (`5_final_output.html`)
- → Saved to output directory

**Post-Processing**:
- `enforce_minimum_requirements()` function adds:
  - Viewport meta tag if missing
  - DOCTYPE if missing

---

### Node 4: STUDENT INTERACTION NODE

**Purpose**: Generates questions, hints, and learning materials for students.

**Input**:
- `spec_json` - Original concept specification
- `plan` - Blueprint JSON from Planner Node

**Processing**:
- LLM Agent: `ChatGoogleGenerativeAI` (gemini-2.5-flash-lite) or OpenRouter model
- Temperature: 0.6 (higher for creativity)
- Creates age-appropriate questions and guidance

**Output**:
- **File**: `4_student_interaction.json`
- **Content**: JSON containing:
  ```json
  {
    "intro": "2-3 line friendly intro",
    "questions": [
      {
        "question": "...",
        "type": "mcq",
        "options": ["A) ...", "B) ...", "C) ...", "D) ..."],
        "hint": "...",
        "correct_index": 0
      }
    ],
    "followups": ["suggestion 1", "suggestion 2"],
    "summary": "Short learning summary"
  }
  ```

**Where Output Goes**:
- → Saved to output directory
- → Can be used to enhance the HTML simulation (not automatically integrated in current flow)

**Note**: This node runs in parallel with Bugfix Node and doesn't directly feed into other nodes in the current implementation.

---

### Node 5: INCORPORATE FEEDBACK NODE (Optional)

**Purpose**: Applies improvements based on feedback to the HTML simulation.

**Input**:
- `html` - HTML file (from Bugfix Node)
- `feedback_text` - Feedback string

**Processing**:
- LLM Agent: `ChatGoogleGenerativeAI` (gemini-2.5-flash-lite) or OpenRouter model
- Temperature: 0.2
- Makes targeted improvements:
  - Updates HTML structure
  - Improves text clarity
  - Adjusts styles
  - Small JavaScript tweaks

**Output**:
- **Format**: JSON response:
  ```json
  {
    "index.html": "<!DOCTYPE html>...",
    "changes_made": ["change 1", "change 2", ...]
  }
  ```

**Where Output Goes**:
- → Can be fed back to Review Node or saved as improved version

**Note**: This node is defined but not actively used in the main flow. It's available for iterative improvement cycles.

---

### Node 6: REVIEW NODE

**Purpose**: Evaluates the final HTML simulation on multiple criteria.

**Input**:
- `html` - Fixed HTML from Bugfix Node

**Processing**:
- LLM Agent: `ChatGoogleGenerativeAI` (gemini-2.5-flash-lite) or OpenRouter model
- Temperature: 0.1 (low for consistency)
- Evaluates on 6 criteria (0-5 scale each):
  1. **Pedagogical clarity** - Learning objectives, explanations, language level
  2. **Conceptual correctness** - Scientific accuracy, misconceptions
  3. **Mobile responsiveness** - Small screens, touch targets, viewport
  4. **Interactivity quality** - Controls, engagement, intuitiveness
  5. **Code reliability** - Valid HTML, no errors, working scripts
  6. **Safety & age appropriateness** - Content for 12-13 year olds

**Output**:
- **File**: `6_review_results.json`
- **Content**: JSON containing:
  ```json
  {
    "scores": {
      "pedagogical_clarity": 0-5,
      "conceptual_correctness": 0-5,
      "mobile_responsiveness": 0-5,
      "interactivity_quality": 0-5,
      "code_reliability": 0-5,
      "safety_age_appropriateness": 0-5
    },
    "pass": true/false,
    "required_changes": ["change 1", "change 2", ...],
    "return_to": "planner/creator/bugfix/none"
  }
  ```

**Pass Criteria**:
- All scores ≥ 3
- Average score ≥ 4

**Where Output Goes**:
- → Saved to output directory
- → Used to determine if simulation passes or needs revision
- → `return_to` field indicates which node to revisit if failed

---

## Output Directory Structure

All outputs are saved in a timestamped directory:

```
output/YYYY-MM-DD_HH-MM-SS_ConceptName/
├── spec.json                          # Input specification (copied)
├── 1_planner_raw_response.txt         # Raw LLM response from Planner
├── 1_planner_blueprint.json            # Parsed blueprint (Node 1 output)
├── 2_creator_raw_response.txt         # Raw LLM response from Creator
├── 2_creator_output.html               # Initial HTML (Node 2 output)
├── 3_bugfix_raw_response.txt          # Raw LLM response from Bugfix
├── 3_bugfix_output.html                # Fixed HTML (Node 3 output)
├── 4_student_interaction.json          # Questions and guidance (Node 4 output)
├── 5_final_output.html                 # Final HTML (Node 3 output, cleaned)
└── 6_review_results.json               # Review scores (Node 6 output)
```

---

## Data Transformation Summary

| Node | Input Type | Output Type | Key Transformation |
|------|-----------|-------------|---------------------|
| **Planner** | JSON (spec) | JSON (blueprint) | Concept → Structured plan |
| **Creator** | JSON (spec + blueprint) | HTML | Plan → Interactive HTML |
| **Bugfix** | HTML | HTML | Broken HTML → Fixed HTML |
| **Student Interaction** | JSON (spec + blueprint) | JSON (questions) | Concept → Learning materials |
| **Incorporate Feedback** | HTML + Text | HTML | HTML + Feedback → Improved HTML |
| **Review** | HTML | JSON (scores) | HTML → Quality assessment |

---

## Key Functions and Utilities

### `safe_json_parse(raw)`
- Extracts JSON from LLM responses
- Handles markdown code blocks
- Falls back to HTML extraction if needed
- Used by all nodes that parse LLM responses

### `extract_html_from_response(response_content)`
- Extracts pure HTML from various formats:
  - JSON wrapped: `{"index.html": "..."}`
  - Markdown wrapped: ` ```html ... ``` `
  - Raw HTML
- Used by Creator and Bugfix nodes

### `check_minimum_requirements(html)`
- Validates HTML has:
  - DOCTYPE
  - Viewport meta tag
  - Interactive controls
  - Styling
- Returns list of issues

### `enforce_minimum_requirements(html)`
- Automatically adds missing viewport and DOCTYPE
- Called after Bugfix Node

### `generate_default_blueprint_from_spec(spec)`
- Fallback function if Planner Node fails
- Creates reasonable default blueprint from spec.json

---

## Error Handling and Fallbacks

1. **Planner Parse Failure**:
   - Retries once
   - Falls back to `generate_default_blueprint_from_spec()`
   - Saves error files for debugging

2. **Creator Parse Failure**:
   - Uses `extract_html_from_response()` to extract HTML
   - Saves error files

3. **Bugfix Parse Failure**:
   - Extracts HTML directly from response
   - Applies `enforce_minimum_requirements()`

4. **Other Node Failures**:
   - Errors are logged
   - System continues with available outputs
   - Error files saved for debugging

---

## Entry Points

### Main Entry: `runner.py` or `open_router_runner.py`

**Command**:
```bash
python src/runner.py --spec spec.json --output-root output
```

**Process**:
1. Loads environment variables
2. Builds all LLM chains
3. Calls `generate_simulation_with_checks()` from `sim_generator.py`
4. Saves all outputs to timestamped directory

### Alternative Entry: `main.py`

**Command**:
```bash
python main.py
```

**Process**:
- Uses built-in chains (not modular)
- Saves outputs to current directory
- Simpler but less flexible

---

## LLM Provider Configuration

The system supports multiple LLM providers:

### Google Gemini (via `runner.py`)
- Uses `ChatGoogleGenerativeAI`
- Models: `gemini-2.5-flash` or `gemini-2.5-flash-lite`
- API Key: `GOOGLE_API_KEY`

### OpenRouter (via `open_router_runner.py`)
- Uses `ChatOpenAI` with custom base_url
- Model: `kwaipilot/kat-coder-pro:free`
- API Key: `OPENROUTER_API_KEY`
- Base URL: `https://openrouter.ai/api/v1`

---

## Complete Execution Flow

```
1. User runs: python src/runner.py --spec spec.json
   ↓
2. System loads spec.json
   ↓
3. Creates timestamped output directory
   ↓
4. PLANNER NODE executes
   - Input: spec.json
   - Output: 1_planner_blueprint.json
   ↓
5. CREATOR NODE executes
   - Input: spec.json + blueprint
   - Output: 2_creator_output.html
   ↓
6. BUGFIX NODE executes
   - Input: HTML from creator
   - Output: 3_bugfix_output.html
   ↓
7. STUDENT INTERACTION NODE executes (parallel)
   - Input: spec.json + blueprint
   - Output: 4_student_interaction.json
   ↓
8. REVIEW NODE executes
   - Input: Fixed HTML
   - Output: 6_review_results.json
   ↓
9. Final HTML saved as 5_final_output.html
   ↓
10. System prints pass/fail status
```

---

## Integration Points

### Where Each Output is Used

1. **`1_planner_blueprint.json`**:
   - → Creator Node (as `plan` parameter)
   - → Student Interaction Node (as `plan` parameter)

2. **`2_creator_output.html`**:
   - → Bugfix Node (as `html` parameter)

3. **`3_bugfix_output.html`**:
   - → Review Node (as `html` parameter)
   - → Final Output (`5_final_output.html`)

4. **`4_student_interaction.json`**:
   - Currently saved but not automatically integrated
   - Can be manually added to HTML or used in future iterations

5. **`6_review_results.json`**:
   - Used to determine pass/fail
   - Contains `return_to` field for iterative improvement

---

## Future Enhancement Opportunities

1. **Automatic Feedback Loop**:
   - Use Review Node's `return_to` field to automatically re-run failed nodes
   - Integrate Incorporate Feedback Node into main flow

2. **Student Interaction Integration**:
   - Automatically embed questions from Node 4 into the HTML
   - Add interactive quiz sections

3. **Iterative Improvement**:
   - Loop back to Bugfix/Creator based on Review scores
   - Multiple refinement cycles

4. **Multi-file Output**:
   - Separate CSS/JS files (currently single-file only)
   - Asset optimization

---

## Summary

This system uses a **sequential agentic pipeline** where:
- Each node transforms data in a specific way
- Outputs flow from one node to the next
- All intermediate outputs are saved for debugging
- Final output is a self-contained HTML simulation
- Quality is assessed by the Review Node

The key insight is that **each node's output becomes the next node's input**, creating a clear data flow from concept specification → blueprint → HTML → fixed HTML → reviewed HTML.

