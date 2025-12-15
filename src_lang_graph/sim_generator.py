# sim_generator.py
"""
Simulation generation using LangGraph with 3 nodes: Planner -> Creator -> Reviewer
"""

import json
from pathlib import Path
from typing import Dict, Any, TypedDict
from datetime import datetime

from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage


# ---------- State Definition ----------

class SimulationState(TypedDict):
    """State that flows through the graph"""
    spec_json: str
    concept_name: str
    planner_raw_output: str        # full planner response
    planner_blueprint: Dict[str, Any]  # parsed JSON (strict)
    creator_output: str
    reviewer_output: Dict[str, Any]
    output_dir: str
    iteration: int
    max_iterations: int
    approved: bool


# ---------- Utilities ----------

def load_spec(path: str) -> Dict[str, Any]:
    """Load spec JSON"""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def sanitize_filename(name: str) -> str:
    """Sanitize string for use in filenames"""
    import re
    sanitized = re.sub(r'[^\w\s-]', '', name)
    sanitized = re.sub(r'[\s_]+', '_', sanitized)
    sanitized = sanitized.strip('_')
    if len(sanitized) > 50:
        sanitized = sanitized[:50]
    return sanitized or "Unknown"


def make_timestamped_output_dir(base_dir: str = "output", concept_name: str = None) -> Path:
    """Create timestamped output directory"""
    now = datetime.now()
    folder_name = now.strftime("%Y-%m-%d_%H-%M-%S")
    
    if concept_name:
        sanitized_concept = sanitize_filename(concept_name)
        folder_name = f"{folder_name}_{sanitized_concept}"
    
    root = Path(base_dir) / folder_name
    root.mkdir(parents=True, exist_ok=True)
    return root


def safe_json_parse(content: str) -> Dict[str, Any]:
    """Parse JSON from LLM response"""
    import re
    
    text = str(content).strip()
    
    # Remove markdown code blocks
    if text.startswith("```"):
        text = text.strip("`").strip()
        if text.lower().startswith("json"):
            text = text[4:].lstrip()
    
    # Try to find JSON object
    match = re.search(r'\{(?:[^{}]|(?:\{[^{}]*\}))*\}', text, re.DOTALL)
    if match:
        json_str = match.group(0)
    else:
        first_brace = text.find('{')
        last_brace = text.rfind('}')
        if first_brace != -1 and last_brace != -1:
            json_str = text[first_brace:last_brace + 1]
        else:
            raise ValueError("Could not find JSON in response")
    
    return json.loads(json_str)


def extract_html_from_response(response_content: str) -> str:
    """Extract HTML from LLM response"""
    text = str(response_content).strip()
    
    # Remove markdown
    if text.startswith("```"):
        text = text.strip("`").strip()
        if text.lower().startswith("html") or text.lower().startswith("json"):
            text = text[4:].lstrip()
    
    # If already HTML
    if text.lstrip().lower().startswith("<!doctype") or text.lstrip().lower().startswith("<html"):
        return text
    
    # Try JSON parse
    try:
        data = json.loads(text)
        if isinstance(data, dict) and "index.html" in data:
            return data["index.html"]
    except json.JSONDecodeError:
        pass
    
    # Find HTML tags
    lower = text.lower()
    doctype_start = lower.find("<!doctype")
    html_start = lower.find("<html")
    
    start_pos = doctype_start if doctype_start != -1 else html_start
    
    if start_pos != -1:
        end_pos = lower.rfind("</html>")
        if end_pos != -1:
            return text[start_pos:end_pos + len("</html>")]
        return text[start_pos:]
    
    return text


def export_prompt_to_file(output_dir: Path, node_name: str, prompt: str):
    """Export prompt template to file"""
    prompt_file = output_dir / f"{node_name}_prompt.txt"
    prompt_file.write_text(prompt, encoding="utf-8")


# ---------- Node Functions ----------

def planner_node(state: SimulationState, planner_chain) -> SimulationState:
    """Planner Node - Creates simulation blueprint"""
    print("\n[PLANNER NODE] Creating blueprint...")
    
    output_dir = Path(state["output_dir"])
    
    try:
        # Invoke planner
        response = planner_chain.invoke({"spec_json": state["spec_json"]})
        raw_content = getattr(response, "content", str(response))
        
        # Save raw response
        (output_dir / "1_planner_raw_response.txt").write_text(
            str(raw_content), encoding="utf-8"
        )

        state["planner_raw_output"] = str(raw_content)
        
        # Parse JSON
        plan_data = safe_json_parse(raw_content)
        plan_json = json.dumps(plan_data, indent=2, ensure_ascii=False)
        
        # Save parsed blueprint
        (output_dir / "1_planner_blueprint.json").write_text(
            plan_json, encoding="utf-8"
        )
        
        print(f"✓ Blueprint created")
        print(f"  Learning objectives: {len(plan_data.get('learning_objectives', []))}")
        print(f"  Variables: {len(plan_data.get('variables_to_simulate', []))}")
        
        # FIX: Use correct state key
        state["planner_blueprint"] = plan_data
        
    except Exception as e:
        print(f"✗ Planner failed: {e}")
        (output_dir / "1_planner_error.txt").write_text(str(e), encoding="utf-8")
        raise
    
    return state


def creator_node(state: SimulationState, creator_chain) -> SimulationState:
    """Creator Node - Generates HTML simulation"""
    print("\n[CREATOR NODE] Generating HTML simulation...")
    
    output_dir = Path(state["output_dir"])
    
    try:
        # FIX: Use correct state key
        blueprint_json = json.dumps(
            state["planner_blueprint"],
            indent=2,
            ensure_ascii=False
        )

        response = creator_chain.invoke({
            "spec_json": state["spec_json"],
            "blueprint": blueprint_json,
            "development_plan": state["planner_raw_output"]
        })

        
        raw_content = getattr(response, "content", str(response))
        
        # Save raw response
        (output_dir / "2_creator_raw_response.txt").write_text(
            str(raw_content), encoding="utf-8"
        )
        
        # Extract HTML
        html = extract_html_from_response(raw_content)
        
        # Ensure basic requirements
        if "<!DOCTYPE html>" not in html and "<!doctype html>" not in html:
            html = "<!DOCTYPE html>\n" + html
        
        if '<meta name="viewport"' not in html.lower():
            if "<head>" in html.lower():
                html = html.replace("<head>", '<head>\n    <meta name="viewport" content="width=device-width, initial-scale=1.0">', 1)
        
        # Save HTML
        (output_dir / "2_creator_output.html").write_text(html, encoding="utf-8")
        
        print(f"✓ HTML generated ({len(html)} bytes)")
        
        state["creator_output"] = html
        
    except Exception as e:
        print(f"✗ Creator failed: {e}")
        (output_dir / "2_creator_error.txt").write_text(str(e), encoding="utf-8")
        raise
    
    return state


def reviewer_node(state: SimulationState, reviewer_chain) -> SimulationState:
    """Reviewer Node - Reviews simulation against blueprint"""
    print("\n[REVIEWER NODE] Reviewing simulation...")
    
    output_dir = Path(state["output_dir"])
    
    try:
        # FIX: Use correct state key
        response = reviewer_chain.invoke({
            "html": state["creator_output"],
            "plan": json.dumps(state["planner_blueprint"], indent=2, ensure_ascii=False)
        })
        
        raw_content = getattr(response, "content", str(response))
        
        # Save raw response
        (output_dir / "3_reviewer_raw_response.txt").write_text(
            str(raw_content), encoding="utf-8"
        )
        
        # Parse review
        review_data = safe_json_parse(raw_content)
        
        # Save review results
        (output_dir / "3_reviewer_results.json").write_text(
            json.dumps(review_data, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )
        
        # Display scores
        scores = review_data.get("scores", {})
        passed = review_data.get("pass", False)
        
        print(f"\n  Scores:")
        for criterion, score in scores.items():
            status = "✓" if score >= 3 else "✗"
            print(f"    {status} {criterion}: {score}/5")
        
        avg_score = sum(scores.values()) / len(scores) if scores else 0
        print(f"\n  Average: {avg_score:.2f}/5.0")
        print(f"  Status: {'✅ APPROVED' if passed else '❌ NEEDS REVISION'}")
        
        if not passed:
            changes = review_data.get("required_changes", [])
            if changes:
                print(f"\n  Required changes:")
                for change in changes[:3]:
                    print(f"    - {change}")
        
        state["reviewer_output"] = review_data
        state["approved"] = passed
        state["iteration"] = state.get("iteration", 0) + 1
        
    except Exception as e:
        print(f"✗ Reviewer failed: {e}")
        (output_dir / "3_reviewer_error.txt").write_text(str(e), encoding="utf-8")
        state["approved"] = False
    
    return state


# ---------- Conditional Edge ----------

def should_continue(state: SimulationState) -> str:
    """Decide whether to end or continue"""
    if state.get("approved", False):
        return "end"
    
    iteration = state.get("iteration", 0)
    max_iterations = state.get("max_iterations", 1)
    
    if iteration >= max_iterations:
        print(f"\n⚠ Reached max iterations ({max_iterations}), stopping...")
        return "end"
    
    print(f"\n↻ Not approved, would iterate (iteration {iteration}/{max_iterations})...")
    # For now, just end after one attempt
    return "end"


# ---------- Graph Builder ----------

def build_graph(planner_chain, creator_chain, reviewer_chain) -> StateGraph:
    """Build the LangGraph workflow"""
    
    workflow = StateGraph(SimulationState)
    
    # Add nodes
    workflow.add_node("planner", lambda state: planner_node(state, planner_chain))
    workflow.add_node("creator", lambda state: creator_node(state, creator_chain))
    workflow.add_node("reviewer", lambda state: reviewer_node(state, reviewer_chain))
    
    # Add edges
    workflow.set_entry_point("planner")
    workflow.add_edge("planner", "creator")
    workflow.add_edge("creator", "reviewer")
    
    # Conditional edge from reviewer
    workflow.add_conditional_edges(
        "reviewer",
        should_continue,
        {
            "end": END,
            "continue": "creator"  # Could loop back to creator for revisions
        }
    )
    
    return workflow.compile()


# ---------- Main Generation Function ----------

def generate_simulation(
    spec_path: str,
    planner_chain,
    creator_chain,
    reviewer_chain,
    output_root: str = "output",
    max_iterations: int = 1,
    prompts: Dict[str, str] = None
) -> tuple[bool, str, Path]:
    """
    Generate simulation using LangGraph
    
    Returns: (approved: bool, html: str, output_dir: Path)
    """
    
    print("=" * 70)
    print("SIMULATION GENERATOR - LangGraph")
    print("=" * 70)
    
    # Load spec
    print("\n[SETUP] Loading specification...")
    try:
        spec = load_spec(spec_path)
        spec_json = json.dumps(spec, indent=2, ensure_ascii=False)
        concept_name = spec.get('Concept', 'Unknown Concept')
        print(f"✓ Concept: {concept_name}")
    except Exception as e:
        print(f"✗ Failed to load spec: {e}")
        output_dir = make_timestamped_output_dir(output_root)
        return False, "", output_dir
    
    # Create output directory
    output_dir = make_timestamped_output_dir(output_root, concept_name)
    print(f"✓ Output directory: {output_dir}")
    
    # Save spec
    (output_dir / "0_spec.json").write_text(spec_json, encoding="utf-8")
    
    # Build graph
    print("\n[SETUP] Building LangGraph workflow...")
    graph = build_graph(planner_chain, creator_chain, reviewer_chain)
    print("✓ Graph compiled")
    
    # FIX: Initialize state with correct types
    initial_state: SimulationState = {
        "spec_json": spec_json,
        "concept_name": concept_name,
        "planner_raw_output": "",  # Initialize as empty string
        "planner_blueprint": {},   # Use correct key name
        "creator_output": "",
        "reviewer_output": {},
        "output_dir": str(output_dir),
        "iteration": 0,
        "max_iterations": max_iterations,
        "approved": False
    }
    
    # Run graph
    print("\n[EXECUTION] Running workflow...")
    print("-" * 70)
    
    try:
        final_state = graph.invoke(initial_state)
        
        # Save final output
        html = final_state.get("creator_output", "")
        approved = final_state.get("approved", False)
        
        (output_dir / "4_final_output.html").write_text(html, encoding="utf-8")
        
        # Save final summary
        summary = {
            "concept": concept_name,
            "approved": approved,
            "iterations": final_state.get("iteration", 0),
            "timestamp": datetime.now().isoformat(),
            "output_dir": str(output_dir)
        }
        (output_dir / "4_summary.json").write_text(
            json.dumps(summary, indent=2), encoding="utf-8"
        )
        
        print("\n" + "=" * 70)
        print("GENERATION COMPLETE")
        print("=" * 70)
        print(f"Status: {'✅ APPROVED' if approved else '⚠ NEEDS REVISION'}")
        print(f"Output: {output_dir}")
        print(f"HTML size: {len(html)} bytes")
        
        return approved, html, output_dir
        
    except Exception as e:
        print(f"\n✗ Workflow failed: {e}")
        (output_dir / "error.txt").write_text(str(e), encoding="utf-8")
        return False, "", output_dir