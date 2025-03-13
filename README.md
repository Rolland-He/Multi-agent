# Multi-Agent Jailbreak Testing System

This system implements a multi-agent framework for testing AI jailbreaking scenarios and ethical boundaries. The system includes three main components:

1. **Invigilator**: Administers questions and evaluates answers
2. **Respondent**: Takes the test and provides answers
3. **Referee**: Monitors interactions for ethical issues and jailbreaking attempts

## Features

- Different jailbreaking modes to test various exploitation scenarios
- Ethics evaluation via the Referee module
- Randomized question selection from a question bank
- Conversation logging and analysis
- Results tracking and metrics

## Setup

### API Key Configuration

1. Copy the template configuration file to create your own config file:
   ```bash
   cp config.template.py config.py
   ```

2. Edit `config.py` and replace the placeholder with your Google Generative AI API key:
   ```python
   GOOGLE_API_KEY = "your_google_api_key_here"
   ```

3. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### Question Bank

The system uses a CSV file containing questions and answers. The default file is `gpqa_main.csv`.

## File Structure

- **main.py**: Orchestrates the interactions between components
- **referee.py**: Implements the ethics evaluation module
- **jailbreak_modes.py**: Defines different jailbreaking scenarios
- **prototype.py**: Contains core functionality (original implementation)
- **logs/**: Directory for storing conversation logs
- **results.csv**: Records test results and metrics

## Usage

Run the system with:

```bash
python main.py [options]
```

### Command Line Options

- `--mode`: Jailbreak mode to test (default: "standard")
  - Available modes: standard, implicit, negotiation, direct_ask, bribery, data_access, social_engineering
- `--question-file`: CSV file containing questions (default: "gpqa_main.csv")
- `--max-turns`: Maximum conversation turns (default: 3)
- `--referee`: Enable Referee's ethics analysis
- `--output`: Base name for output files (default: "results")

### Example

```bash
python main.py --mode bribery --referee
```

## Jailbreak Modes

- **standard**: No jailbreaking attempts
- **implicit**: No explicit jailbreaking instructions, tests natural tendencies
- **negotiation**: Respondent tries to negotiate with the Invigilator
- **direct_ask**: Respondent directly asks for answers
- **bribery**: Respondent offers incentives for help
- **data_access**: Respondent attempts to access test data
- **social_engineering**: Respondent tries to manipulate the Invigilator

## Ethics Evaluation

The Referee module analyzes conversations for:
- Direct answer requests
- Manipulation attempts
- Negotiation tactics
- Bribery attempts
- Data access attempts
- Rule circumvention
- Policy violations
- Social engineering

Each interaction receives an Ethics Integrity Score (0-10) and detailed analysis.

## Output

Results are saved in:
- **results.csv**: Summary of all test runs
- **logs/results_[mode]_[timestamp].txt**: Detailed conversation logs and analysis