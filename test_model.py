import requests
import json

from config import Config

# --- Configuration ---
MODEL_NAME = Config.MODEL_NAME
OLLAMA_BASE_URL = f"{Config.OLLAMA_BASE_URL}/api/generate"
TEMPERATURE = Config.TEMPERATURE

def test_remote_ollama(prompt):
    payload = {
        "model": MODEL_NAME,
        "prompt": prompt,
        "stream": False,  # Set to True for real-time word generation
        "options": {
            "temperature": TEMPERATURE
        }
    }

    print(f"Connecting to: {OLLAMA_BASE_URL}...")
    
    try:
        response = requests.post(
            OLLAMA_BASE_URL, 
            json=payload, 
            timeout=30  # Generous timeout for remote latency
        )
        
        # Check if the request was successful
        response.raise_for_status()
        
        # Parse the result
        result = response.json()
        print("\n--- Model Response ---")
        print(result.get("response", "No response field found."))
        print("----------------------")
        print(f"Total duration: {result.get('total_duration')}")

    except requests.exceptions.ConnectionError:
        print("Error: Could not connect to the server. Check the IP and ensure Ollama is running.")
    except requests.exceptions.HTTPError as e:
        print(f"Error: The server returned an error. Status code: {response.status_code}")
        print(f"Details: {response.text}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    test_prompt = "Why is the sky blue? Give me a one-sentence answer."
    test_remote_ollama(test_prompt)