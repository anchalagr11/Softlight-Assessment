# AI Web Automation Agent

A powerful, AI-driven web automation tool that leverages Google's Gemini models to understand natural language instructions and execute complex tasks on the web. This project uses a sophisticated agent architecture to plan, execute, and adapt to dynamic web interfaces.

## Key Features

*   **Natural Language Interface:** Simply describe your task in plain English (e.g., "Log into Linear and create a new issue for the backend team").
*   **Intelligent Planning:** An **Orchestrator Agent** breaks down high-level objectives into a logical sequence of steps.
*   **Robust Execution:** The **Action Engine** is built to handle the flakiness of web automation. It supports:
    *   Dynamic and fuzzy selector matching (text, role, labels).
    *   Automatic handling of modals, menus, and overlays.
    *   Smart fallbacks for typing and clicking.
*   **Graph-Based Architecture:** Built on `langgraph` to manage agent state, loops, and decision-making processes.
*   **Browser Persistence:** Option to keep the browser session open after task completion for verification or manual takeover.

## Prerequisites

*   Python 3.8 or higher
*   A Google Cloud Project with the Gemini API enabled
*   An API Key for Google Gemini

## Installation

1.  **Clone the repository:**
    ```bash
    git clone <repository-url>
    cd Softlight_Assesment
    ```

2.  **Create and activate a virtual environment (recommended):**
    ```bash
    python -m venv venv
    # Windows
    venv\Scripts\activate
    # macOS/Linux
    source venv/bin/activate
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Install Playwright browsers:**
    ```bash
    playwright install
    ```

## Configuration

1.  Create a `.env` file in the root directory of the project.
2.  Add your Google Gemini API key:

    ```env
    GEMINI_API_KEY=your_actual_api_key_here
    ```

## Usage

The main entry point is `src/main.py`. You can run it from the command line by providing a task description.

### Basic Usage

```bash
python src/main.py --task "Go to Google and search for 'latest AI trends'"

python src/main.py --task "Go to Notion and create a new page with the Title 'Proejct A'"
```

### Keep Browser Open

To keep the browser open after the task completes (useful for debugging or verifying results):

```bash
python src/main.py --task "Navigate to example.com" --keep-open
```

## TB Project Structure

*   `src/agents`: Contains the logic for different agents (Orchestrator, Executor).
*   `src/automation`: Core automation logic, including the `ActionEngine` and `DOMTree` analysis.
*   `src/llm`: Handles interactions with the Google Gemini API.
*   `src/graph`: Defines the `langgraph` workflow and nodes.
*   `src/dataset`: Used for storing execution data or examples.
*   `src/main.py`: The application entry point.

## License

[MIT License](LICENSE)
