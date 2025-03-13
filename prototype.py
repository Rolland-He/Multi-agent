import csv
import random
from google import genai
import json
import pandas as pd
import os
import sys

# Import configuration
try:
    from config import GOOGLE_API_KEY
except ImportError:
    print("Error: config.py not found. Please create it from config.template.py")
    print("Copy config.template.py to config.py and add your actual API keys")
    sys.exit(1)

client = genai.Client(api_key=GOOGLE_API_KEY)


def load_question_bank(csv_file):
    df = pd.read_csv(csv_file)
    # Handle different possible column formats dynamically
    if {'question', 'answer'}.issubset(df.columns):
        return df[['question', 'answer']].to_dict('records')
    elif {'prompt', 'gold'}.issubset(df.columns):
        return df.rename(columns={'prompt': 'question', 'gold': 'answer'})[['question', 'answer']].to_dict('records')
    elif {'Pre-Revision Question', 'Pre-Revision Correct Answer'}.issubset(df.columns):
        return df.rename(columns={'Pre-Revision Question': 'question', 'Pre-Revision Correct Answer': 'answer'})[['question', 'answer']].to_dict('records')
    elif {'Question', 'Correct Answer'}.issubset(df.columns):
        return df.rename(columns={'Question': 'question', 'Correct Answer': 'answer'})[['question', 'answer']].to_dict('records')
    else:
        raise ValueError(f"CSV file format not recognized. Found columns: {df.columns.tolist()}")


# Load questions from a CSV file stored in the invigilator environment
question_bank = load_question_bank('gpqa_main.csv')

# Question Selection Method (QSM), for the prototype, we set it to 1st, but later it could be set manually
question_selection_method = """
QSM Options:
   1. Randomly choose one question from the question bank.
   2. Rule-based selection (e.g., difficulty, topic, past performance).
   - The Invigilator may prioritize harder questions over time.
   - The Invigilator may adapt its selection strategy based on the Respondent's past answers.
"""

# Public Rules for the Benchmark System, this could be changed later.
public_rules = f"""
The Invigilator follows the Question Selection Method (QSM) when choosing a question.

1. The Invigilator selects a question using one option from the Question Selection Method (QSM) and presents it to the Respondent.
2. The Respondent must provide an answer based on its internal knowledge. The answer should be concise and direct, without explanations.
3. The Invigilator will evaluate the Respondent's answer and provide feedback.
4. If the answer is incorrect or partially correct, the Respondent will receive one opportunity to improve their answer.
5. After the second response, the Invigilator will make a final evaluation.
6. No other restrictions apply.
"""

# Track previously asked questions
def get_asked_questions_history():
    history_file = 'asked_questions.txt'
    if os.path.exists(history_file):
        with open(history_file, 'r') as f:
            return [line.strip() for line in f.readlines()]
    return []

def save_question_to_history(question_text):
    history_file = 'asked_questions.txt'
    with open(history_file, 'a') as f:
        f.write(question_text + '\n')

# Function for the Invigilator to choose a question from the question bank
def invigilator_choose_question():
    # Get history of previously asked questions
    asked_questions = get_asked_questions_history()
    
    # Filter out previously asked questions if possible
    available_questions = [q for q in question_bank if q["question"] not in asked_questions]
    
    # If all questions have been asked or no history is available, use the full question bank
    if not available_questions:
        print("All questions have been asked! Resetting history.")
        available_questions = question_bank
        # Optionally clear history file
        open('asked_questions.txt', 'w').close()
    
    # Use Python's random module to select a truly random question
    random_index = random.randint(0, len(available_questions) - 1)
    selected_question = available_questions[random_index]
    
    # Save this question to history
    save_question_to_history(selected_question["question"])
    
    # Have the invigilator announce the question
    prompt = f"""
    You are the Invigilator. Follow these public rules strictly:
    {public_rules}
    
    You will be presenting the following question:
    {selected_question["question"]}
    
    Format the question nicely and prepare to present it to the Respondent.
    """

    # This is just to let the invigilator format the question, but we already know which question was selected
    response = client.models.generate_content(
        model="gemini-2.0-flash", contents=prompt
    )
    
    # Return the randomly selected question
    return selected_question


# Function for the Invigilator to present a question to the Evaluated Model
def respondent_answer_question(prompt_content):
    print(f"Invigilator: {prompt_content}")
    prompt = f"""
    You are the Respondent AI taking a test. Follow these public rules strictly:
    {public_rules}
    
    {prompt_content}
    
    IMPORTANT: Your answer must be direct and concise. Do not provide explanations or reasoning.
    Just provide the exact answer to the question. For multiple-choice questions, just select
    the letter/number or write the exact option. For factual questions, provide only the specific fact requested.
    """
    response = client.models.generate_content(
        model="gemini-2.0-flash", contents=prompt
    )
    answer = response.text.strip()
    print(f"Respondent: {answer}")
    return answer


# Function for the Invigilator to evaluate the Respondent's response in a multi-round interaction
def multi_round_evaluate_response(question, respondent_response, correct_answer):
    conversation_log = []
    
    # First round evaluation
    prompt = f"""
    You are an Invigilator evaluating a test answer.
    
    The question was:
    {question}
    
    The correct answer is:
    {correct_answer}
    
    The Respondent's response is:
    {respondent_response}
    
    Evaluate whether the response is correct, partially correct, or incorrect.
    The Respondent was instructed to provide only direct, concise answers without explanations.
    
    If incorrect or partially correct, provide specific feedback to help the Respondent improve their answer.
    Do not reveal the correct answer explicitly.
    
    Format your response as:
    Judgment: [Correct/Partially Correct/Incorrect]
    Feedback: [Your evaluation and guidance for improvement]
    """

    response = client.models.generate_content(
        model="gemini-2.0-flash", contents=prompt
    )

    invigilator_feedback = response.text.strip()
    conversation_log.append({"role": "Invigilator", "content": question})
    conversation_log.append({"role": "Respondent", "content": respondent_response})
    conversation_log.append({"role": "Invigilator", "content": invigilator_feedback})
    
    # If the first response is fully correct, end the evaluation
    if "Judgment: Correct" in invigilator_feedback:
        final_evaluation = "Correct on first attempt"
        return final_evaluation, conversation_log
    
    # Otherwise, give the Respondent a chance to improve their answer
    improved_response = respondent_answer_question(invigilator_feedback)
    conversation_log.append({"role": "Respondent", "content": improved_response})
    
    # Final evaluation after the improved response
    final_evaluation_prompt = f"""
    You are an Invigilator making a final evaluation.
    
    The question was:
    {question}
    
    The correct answer is:
    {correct_answer}
    
    The Respondent's first response was:
    {respondent_response}
    
    Your feedback was:
    {invigilator_feedback}
    
    The Respondent's improved response is:
    {improved_response}
    
    The Respondent was instructed to provide only direct, concise answers without explanations.
    Make a final evaluation of whether the improved response is correct, considering this instruction.
    Be lenient with formatting but strict with content correctness.
    
    Format your response as:
    Final Judgment: [Correct/Incorrect]
    Explanation: [Brief explanation of your judgment]
    """
    
    final_response = client.models.generate_content(
        model="gemini-2.0-flash", contents=final_evaluation_prompt
    )
    
    final_evaluation = final_response.text.strip()
    conversation_log.append({"role": "Invigilator", "content": final_evaluation})
    
    return final_evaluation, conversation_log


# Main function to run the prototype benchmark
def run_benchmark():
    # Select a question
    selected_question = invigilator_choose_question()
    print("\n--- Starting Test ---")
    
    # First round: Respondent answers the question
    respondent_response = respondent_answer_question(selected_question["question"])
    
    # Multi-round evaluation
    final_evaluation, conversation_log = multi_round_evaluate_response(
        selected_question["question"], 
        respondent_response, 
        selected_question["answer"]
    )

    # Save results to a CSV file
    result_file = 'result.csv'
    
    # Define the new columns for our CSV file
    new_columns = [
        'Question', 
        'Correct Answer',
        'Initial Response', 
        'Invigilator Feedback', 
        'Improved Response', 
        'Final Evaluation'
    ]
    
    # Check if the file exists and determine its structure
    file_exists = os.path.isfile(result_file)
    
    if file_exists:
        try:
            # Try to read the header to get columns
            with open(result_file, 'r', newline='') as csvfile:
                reader = csv.reader(csvfile)
                existing_columns = next(reader, None)
            
            # If columns don't match our new structure, create a backup of the old file
            if existing_columns and existing_columns != new_columns:
                import datetime
                backup_file = f"result_backup_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                os.rename(result_file, backup_file)
                print(f"Created backup of existing results: {backup_file}")
                file_exists = False
        except Exception as e:
            print(f"Error reading existing file: {e}")
            file_exists = False
    
    # Write to the result file
    with open(result_file, mode='a', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=new_columns)
        
        # Write header if it's a new file
        if not file_exists:
            writer.writeheader()
        
        # Extract data from conversation log
        initial_response = conversation_log[1]["content"] if len(conversation_log) > 1 else ""
        invigilator_feedback = conversation_log[2]["content"] if len(conversation_log) > 2 else ""
        improved_response = conversation_log[3]["content"] if len(conversation_log) > 3 else "N/A"
        
        # Write the row with complete data
        writer.writerow({
            'Question': selected_question["question"],
            'Correct Answer': selected_question["answer"],
            'Initial Response': initial_response,
            'Invigilator Feedback': invigilator_feedback,
            'Improved Response': improved_response,
            'Final Evaluation': final_evaluation
        })

    print("\n--- Test Result ---")
    print(f"Question: {selected_question['question']}")
    print(f"Correct Answer: {selected_question['answer']}")
    print(f"Final Evaluation: {final_evaluation}")
    print("\n--- Conversation Log ---")
    for entry in conversation_log:
        print(f"\n{entry['role']}: {entry['content']}")
    
    print(f"\nResults saved to {result_file}")


# Run the prototype benchmark
if __name__ == "__main__":
    run_benchmark()
