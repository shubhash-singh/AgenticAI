# AI-Powered Educational Simulation Generator

This project uses a multi-agent AI pipeline to automatically generate, debug, and review simple, interactive, mobile-first educational simulations from a JSON specification.

## How It Works

The project is orchestrated by `main.py` and follows a three-step process:

1.  **Creation**: A "creator" agent (`llama-3.3-70b-versatile` via Groq) receives a JSON file (`spec.json`) describing an educational concept. It generates a single, self-contained HTML file with vanilla JavaScript and inline CSS to create an interactive simulation.

2.  **Bug-Fixing**: A "bug-fixer" agent (`openai/gpt-oss-20b` via Groq) inspects the generated HTML for any syntax errors, layout issues on mobile, or broken JavaScript. It automatically corrects any issues it finds.

3.  **Review**: A "reviewer" agent (`qwen/qwen3-32b` via Groq) performs a final quality check on the HTML. It ensures the simulation is mobile-friendly, interactive, and clearly explains the concept.

This cycle repeats up to three times until the simulation is approved by the reviewer. The final, polished `simulation.html` is then saved to disk.

The included example generates a **Projectile Motion Simulator**.

## Project Structure

-   `main.py`: The main script that orchestrates the agent pipeline.
-   `spec.json`: The input file that defines the simulation to be created. You can modify this to generate different simulations.
-   `simulation.html`: The final, generated output file.
-   `.env`: The file to store your API keys (see Setup).
-   `SimulationAgent/`: (Currently unused) Intended for more complex agent logic.

## Technologies Used

-   **Python**
-   **LangChain** for orchestrating the AI models.
-   **Groq** for high-speed inference with open-source LLMs.
-   **AI Models**:
    -   `llama-3.3-70b-versatile`: For creative code generation.
    -   `openai/gpt-oss-20b`: For technical bug fixing.
    -   `qwen/qwen3-32b`: For final review and quality assurance.
-   **HTML, CSS, JavaScript** (in the generated output).

## Setup

1.  **Clone the repository.**

2.  **Install Python dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
    *(Note: A `requirements.txt` file would need to be created from the virtual environment if not present.)*

3.  **Create a `.env` file** in the root of the project and add your Groq API keys:
    ```
    GROQ_API_KEY_GENERATE_SIMULATION="your_groq_api_key"
    GROQ_API_KEY_FIX_BUGS="your_groq_api_key"
    GROQ_API_KEY_REVIEW="your_groq_api_key"
    ```
    *(You can use the same key for all three if you wish.)*

## How to Run

Execute the main script from your terminal:

```bash
python main.py
```

The script will print its progress through the creation, bug-fixing, and review steps. Once complete, you can open `simulation.html` in your web browser to see the result.

## Customizing the Simulation

To create a different simulation, modify the `spec.json` file. The keys in this JSON object guide the creation agent. For example, you could change the `title`, `concept`, and `learning_objectives` to describe a different topic.
