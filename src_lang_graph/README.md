# Simulation Generator - LangGraph Refactor

## Overview

Refactored simulation generator using **LangGraph** with a simplified 3-node workflow:

```
Planner → Creator → Reviewer → (END or loop back to Creator)
```

## Key Changes

### 1. **Simplified Architecture**
- **Removed nodes**: Bugfix, Student Interaction, Incorporate Feedback
- **Kept nodes**: Planner, Creator, Reviewer
- **LangGraph**: Replaced custom orchestration with LangGraph's state machine

### 2. **Output Structure**

All outputs are saved in timestamped directories:
```
output/YYYY-MM-DD_HH-MM-SS_ConceptName/
├── 0_spec.json                    # Input specification
├── 0_planner_prompt.txt           # Planner prompt template
├── 0_creator_prompt.txt           # Creator prompt template
├── 0_reviewer_prompt.txt          # Reviewer prompt template
├── 1_planner_raw_response.txt     # Raw LLM output from planner
├── 1_planner_blueprint.json       # Parsed planner blueprint
├── 2_creator_raw_response.txt     # Raw LLM output from creator
├── 2_creator_output.html          # Generated HTML simulation
├── 3_reviewer_raw_response.txt    # Raw LLM output from reviewer
├── 3_reviewer_results.json        # Parsed review results
├── 4_final_output.html            # Final simulation (copy of creator output)
└── 4_summary.json                 # Generation summary
```

### 3. **Workflow**

#### Node 1: Planner
- **Input**: `spec.json` (concept specification)
- **Output**: Blueprint JSON with:
  - Learning objectives
  - Visual design plan
  - Variables to simulate
  - Layout structure
  - Simulation logic steps
- **Saved**: Prompt, raw response, parsed blueprint

#### Node 2: Creator
- **Input**: Blueprint from Planner + original spec
- **Output**: Complete HTML simulation
- **Checks**: 
  - Blueprint adherence
  - All variables implemented
  - Visual design matches plan
- **Saved**: Prompt, raw response, HTML output

#### Node 3: Reviewer
- **Input**: HTML from Creator + Blueprint from Planner
- **Output**: Quality scores and approval decision
- **Evaluates**:
  - Blueprint adherence (are all planned features present?)
  - Pedagogical clarity
  - Conceptual correctness
  - Mobile responsiveness
  - Interactivity quality
  - Code quality
- **Decision**: Pass (≥4.0 avg, all scores ≥3) or Needs Revision
- **Saved**: Prompt, raw response, review results

## Installation

```bash
pip install -r requirements.txt
```

## Configuration

Create `.env` file:
```
GOOGLE_API_KEY=your_gemini_api_key_here
```

## Usage

```bash
python runner.py --spec spec.json --output-root output
```

### Arguments:
- `--spec, -s`: Path to specification JSON (default: `spec.json`)
- `--output-root`: Output directory root (default: `output`)
- `--max-iterations`: Maximum revision iterations (default: `1`)

## Spec JSON Format

```json
{
  "Concept": "Photosynthesis",
  "Description": "Interactive simulation of the photosynthesis process",
  "Target_Age": "12-13 years (Class 7)",
  "Key_Topics": [
    "Light absorption",
    "Chlorophyll role",
    "Oxygen production"
  ]
}
```

## LangGraph State

The state flows through nodes:

```python
class SimulationState(TypedDict):
    spec_json: str                    # Input specification
    concept_name: str                 # Concept name for folder
    planner_output: Dict              # Planner blueprint
    creator_output: str               # HTML simulation
    reviewer_output: Dict             # Review results
    output_dir: str                   # Output directory path
    iteration: int                    # Current iteration
    max_iterations: int               # Max iterations allowed
    approved: bool                    # Approval status
```

## Reviewer Scoring

Each criterion scored 0-5:

1. **Blueprint Adherence** - Does HTML match the plan?
2. **Pedagogical Clarity** - Clear learning for Class 7?
3. **Conceptual Correctness** - Scientifically accurate?
4. **Mobile Responsiveness** - Works on small screens?
5. **Interactivity Quality** - Engaging and smooth?
6. **Code Quality** - Clean, error-free code?

**Passing criteria:**
- All scores ≥ 3
- Average score ≥ 4.0
- All blueprint features present

## Benefits of LangGraph Version

1. **Clear workflow**: Visual graph of node dependencies
2. **State management**: Structured state passed between nodes
3. **Extensibility**: Easy to add conditional branches or loops
4. **Debugging**: Each node output saved separately
5. **Prompt transparency**: All prompts exported to files
6. **Blueprint validation**: Reviewer checks if Creator followed the plan

## Future Enhancements

- Add conditional loop: If not approved, send feedback to Creator for revision
- Add parallel review nodes for different quality aspects
- Add human-in-the-loop approval step
- Add A/B testing node to compare multiple generations

## Example Output

```
======================================================================
SIMULATION GENERATOR - LangGraph
======================================================================

[SETUP] Loading specification...
✓ Concept: Photosynthesis
✓ Output directory: output/2025-12-15_14-30-45_Photosynthesis

[SETUP] Exporting prompts...
✓ Prompts exported

[SETUP] Building LangGraph workflow...
✓ Graph compiled

[EXECUTION] Running workflow...
----------------------------------------------------------------------

[PLANNER NODE] Creating blueprint...
✓ Blueprint created
  Learning objectives: 3
  Variables: 2

[CREATOR NODE] Generating HTML simulation...
✓ HTML generated (15234 bytes)

[REVIEWER NODE] Reviewing simulation...

  Scores:
    ✓ blueprint_adherence: 5/5
    ✓ pedagogical_clarity: 4/5
    ✓ conceptual_correctness: 5/5
    ✓ mobile_responsiveness: 4/5
    ✓ interactivity_quality: 4/5
    ✓ code_quality: 4/5

  Average: 4.33/5.0
  Status: ✅ APPROVED

======================================================================
GENERATION COMPLETE
======================================================================
Status: ✅ APPROVED
Output: output/2025-12-15_14-30-45_Photosynthesis
HTML size: 15234 bytes
```

## Troubleshooting

### Issue: JSON parsing fails
- Check raw response files (`*_raw_response.txt`)
- LLM may have added markdown or explanations
- Adjust prompts to emphasize "JSON ONLY"

### Issue: Review always fails
- Check `3_reviewer_results.json` for specific issues
- Review `required_changes` array
- May need to adjust reviewer thresholds

### Issue: HTML is incomplete
- Check `2_creator_output.html`
- Verify blueprint has sufficient detail
- May need to enhance planner prompt

## License

MIT