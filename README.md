# CBSE Simulation Generator


## 🎯 Overview

This system uses multiple specialized LLM agents to automatically generate high-quality, interactive educational simulations from simple concept specifications. Each agent has a specific role in the generation pipeline, ensuring pedagogically sound, technically correct, and engaging learning experiences.

## ✨ Features

- **Multi-Agent Architecture**: Six specialized agents (Planner, Creator, Bugfix, Student Interaction, Feedback, Review)
- **Mobile-First Design**: All simulations optimized for 360px+ screens with touch-friendly controls
- **Self-Contained HTML**: Single-file outputs with no external dependencies
- **Visual Learning Focus**: Emphasizes graphics and animations over text
- **Quality Assurance**: Built-in review system with scoring across 6 criteria
- **Intermediate Saves**: All agent outputs saved for debugging and analysis
- **Flexible LLM Backend**: Uses OpenRouter API with configurable models

## 📋 Requirements

- Python 3.8+
- OpenRouter API key
- Required Python packages:
  - `langchain-core`
  - `langchain-openai`
  - `python-dotenv`

## 🚀 Installation

1. **Clone the repository**:
   ```bash
   git clone <your-repo-url>
   cd simulation-generator
   ```

2. **Install dependencies**:
   ```bash
   pip install langchain-core langchain-openai python-dotenv
   ```

3. **Set up environment variables**:
   Create a `.env` file in the project root:
   ```env
   OPENROUTER_API_KEY=your_openrouter_api_key_here
   ```

4. **Get an OpenRouter API key**:
   - Visit [OpenRouter.ai](https://openrouter.ai/)
   - Sign up and get your API key
   - Add credits to your account

## 📝 Usage

### Basic Usage

1. **Create a spec file** (`spec.json`):
   ```json
   {
     "Concept": "Photosynthesis",
     "Description": "Learn how plants convert sunlight into energy through photosynthesis",
     "Grade": 7,
     "Subject": "Science",
     "Topic": "Nutrition in Plants"
   }
   ```

2. **Run the generator**:
   ```bash
   python open_router_runner.py --spec spec.json
   ```

3. **View the output**:
   - Open `output/YYYY-MM-DD_HH-MM-SS_ConceptName/5_final_output.html` in a browser

### Advanced Options

```bash
# Custom output directory
python open_router_runner.py --spec spec.json --output-root my_outputs

# Don't save intermediate files (faster, less disk space)
python open_router_runner.py --spec spec.json --no-save-intermediates

# Show help
python open_router_runner.py --help
```

## 🏗️ Project Structure

```
simulation-generator/
├── open_router_runner.py      # Main CLI entry point
├── sim_generator.py            # Core orchestration logic
├── spec.json                   # Example concept specification
├── .env                        # Environment variables (not in repo)
├── README.md                   # This file
└── output/                     # Generated simulations (created automatically)
    └── YYYY-MM-DD_HH-MM-SS_ConceptName/
        ├── spec.json                           # Input specification
        ├── 1_planner_raw_response.txt         # Raw planner output
        ├── 1_planner_blueprint.json           # Parsed blueprint
        ├── 2_creator_raw_response.txt         # Raw creator output
        ├── 2_creator_output.html              # Initial HTML
        ├── 3_bugfix_raw_response.txt          # Raw bugfix output
        ├── 3_bugfix_output.html               # Fixed HTML
        ├── 4_student_interaction.json         # Generated questions
        ├── 5_final_output.html                # ✨ Final simulation
        └── 6_review_results.json              # Quality review scores
```

## 🤖 Agent Architecture

### 1. **Planner Agent** (Temperature: 0.3)
- Analyzes concept specification
- Creates detailed blueprint with visual design, variables, and layout
- Ensures mobile-first and visual-learning principles

### 2. **Creator Agent** (Temperature: 0)
- Receives raw planner output
- Generates complete, self-contained HTML simulation
- Implements responsive design with proper centering and touch targets

### 3. **Bugfix Agent** (Temperature: 0.2)
- Fixes structural, layout, and positioning issues
- Ensures mobile responsiveness
- Adds missing meta tags and validates HTML

### 4. **Student Interaction Agent** (Temperature: 0.6)
- Creates 3 progressive difficulty MCQ questions
- Generates hints and explanations
- Provides follow-up exploration prompts

### 5. **Feedback Integration Agent** (Temperature: 0.2)
- Applies user-requested improvements
- Maintains quality while implementing changes
- Documents all modifications

### 6. **Review Agent** (Temperature: 0.1)
- Scores simulation across 6 criteria (each 0-5):
  - Pedagogical Clarity
  - Conceptual Correctness
  - Mobile Responsiveness
  - Interactivity Quality
  - Code Reliability
  - Safety & Age Appropriateness
- Minimum passing: All scores ≥3, average ≥4.0

## ⚙️ Configuration

### Changing LLM Models

Edit `open_router_runner.py` in the `build_all_chains()` function:

```python
planner_llm = ChatOpenAI(
    model="anthropic/claude-3.5-sonnet",  # Change model here
    temperature=0.3,
    api_key=os.getenv("OPENROUTER_API_KEY"),
    base_url="https://openrouter.ai/api/v1",
)
```

### Available Models on OpenRouter

- Free tier: `kwaipilot/kat-coder-pro:free`
- Claude: `anthropic/claude-3.5-sonnet`, `anthropic/claude-3-opus`
- GPT: `openai/gpt-4-turbo`, `openai/gpt-3.5-turbo`
- Many more at [OpenRouter Models](https://openrouter.ai/models)

### Adjusting Temperature

- **Lower (0-0.3)**: More deterministic, consistent outputs (Bugfix, Review)
- **Medium (0.3-0.6)**: Balanced creativity (Planner, Feedback)
- **Higher (0.6-1.0)**: More creative variations (Student Interaction)

## 📊 Output Structure

Each run creates a timestamped folder containing:

| File | Description |
|------|-------------|
| `spec.json` | Your input specification |
| `1_planner_*` | Planner agent outputs (raw + parsed) |
| `2_creator_*` | Creator agent outputs (raw + HTML) |
| `3_bugfix_*` | Bugfix agent outputs |
| `4_student_interaction.json` | MCQ questions and hints |
| `5_final_output.html` | **Main deliverable** - Open in browser |
| `6_review_results.json` | Quality scores and feedback |

## 🎨 Simulation Features

Generated simulations include:

- **Visual Elements**: SVG graphics, animations, color schemes
- **Interactive Controls**: Sliders, buttons, toggles (≥48px touch targets)
- **Real-time Feedback**: Immediate visual responses to input
- **Responsive Layout**: Works on mobile (360px+) and desktop
- **Educational Content**: Instructions, current values, observations
- **No External Dependencies**: Self-contained, works offline

## 🐛 Troubleshooting

### "No module named 'langchain_core'"
```bash
pip install langchain-core langchain-openai
```

### "API key not found"
- Check that `.env` file exists in project root
- Verify `OPENROUTER_API_KEY` is set correctly
- Make sure `.env` is in same directory as `open_router_runner.py`

### "Rate limit exceeded"
- OpenRouter free tier has rate limits
- Add credits to your OpenRouter account
- Wait a few minutes between runs

### Simulation not displaying correctly
- Check browser console (F12) for JavaScript errors
- Verify the HTML file is complete (not truncated)
- Review intermediate files in output folder for issues

### Low review scores
- Check `6_review_results.json` for specific issues
- Review `required_changes` array for actionable feedback
- Try running again with clearer spec description

## 🔧 Customization

### Adding New Agents

1. Create prompt template in `open_router_runner.py`
2. Build chain in `build_all_chains()`
3. Add invocation in `sim_generator.py`
4. Update return tuple

### Modifying Prompts

Edit the prompt templates in `open_router_runner.py`:
- `planner_prompt` - Blueprint creation guidelines
- `creation_prompt` - HTML generation instructions
- `bugfix_prompt` - Fix checklist
- `student_interaction_prompt` - Question design rules
- `review_prompt` - Scoring criteria

### Changing Quality Thresholds

Edit `review_prompt` in `open_router_runner.py`:
```python
PASSING CRITERIA:
- ALL scores must be ≥ 3  # Change minimum score
- Average score must be ≥ 4.0  # Change average requirement
```

## 📚 Example Concepts

Good spec.json examples:

```json
{
  "Concept": "States of Matter",
  "Description": "Explore how temperature affects particles in solids, liquids, and gases"
}
```

```json
{
  "Concept": "Photosynthesis",
  "Description": "Interactive model showing how plants make food using sunlight, water, and CO2"
}
```

```json
{
  "Concept": "Simple Pendulum",
  "Description": "Adjust length and mass to see how they affect a pendulum's swing period"
}
```

## 📄 License

[Specify your license here - e.g., MIT, Apache 2.0, GPL, etc.]

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📧 Contact

[Your contact information or project maintainer details]

## 🙏 Acknowledgments

- Built with [LangChain](https://www.langchain.com/)
- Powered by [OpenRouter](https://openrouter.ai/)
- Designed for CBSE curriculum

---

**Note**: This is an AI-powered tool. Always review generated content for accuracy and appropriateness before use in educational settings.