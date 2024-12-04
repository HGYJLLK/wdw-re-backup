import requests
import json

def generate_english_sentences(word_sequence, model_name="llama2"):
    """Generate a coherent sentence using all given words."""
    prompt = f"""
Create a short story consisting of 3 brief sentences using the following words:
{', '.join(word_sequence)}

Requirements:
1. Each sentence should use at least 1 of the given words.
2. Sentences should be in English and use everyday language.
3. The 3 sentences should form a simple but coherent short story.
4. Return only the sentences, without any explanations or extra information.
5. Each sentence should be on a separate line.
6. Each sentence should not exceed 8 words.
"""

    try:
        response = requests.post('http://localhost:11434/api/completions',
                                 json={"model": model_name, "prompt": prompt},
                                 stream=True)
        response.raise_for_status()

        # Collect the responses
        full_response = ''
        for line in response.iter_lines():
            if line:
                line = line.decode('utf-8')
                try:
                    data = json.loads(line)
                    if 'response' in data:
                        full_response += data['response']
                except json.JSONDecodeError as e:
                    print(f"JSON decode error: {e}")
                    continue

        # Split the response into sentences
        sentences = [sent.strip() for sent in full_response.strip().split('\n') if sent.strip()]
        return sentences

    except requests.RequestException as e:
        print(f"Request exception: {e}")
        return [f"Error generating sentences: {e}"]
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return [f"An unexpected error occurred: {e}"]

if __name__ == '__main__':
    mode = input("Choose mode - Single word (s) or Connect words (c): ").strip().lower()
    connect_words = mode == 'c'
    word_sequence = []

    while True:
        word = input("Enter a word (or 'quit' to exit): ").strip()
        if word.lower() == 'quit':
            break
        word_sequence.append(word)
        sentences = generate_english_sentences(word_sequence)
        print("Generated Sentences:")
        for sentence in sentences:
            print(sentence)
