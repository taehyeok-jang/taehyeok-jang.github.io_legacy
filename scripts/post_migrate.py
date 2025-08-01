import os
import requests
import yaml

OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
POST_PATH = os.environ.get('POST_PATH')
TARGET_DIR = os.environ.get('TARGET_DIR')
TOBE_REPO_PATH = os.environ.get('TOBE_REPO_PATH')

def call_api(prompt):
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {OPENAI_API_KEY}"
    }
    data = {
        "model": "gpt-4o",
        "messages": [{"role": "user", "content": prompt}]
    }
    
    

    for attempt in range(5):
        response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=data)
        
        if response.status_code == 429:
            wait_time = 10 * (attempt + 1)
            print(f"Rate limited. Retrying in {wait_time} seconds...")
            time.sleep(wait_time)
            continue

        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]

    raise Exception("Too many retries")

def process_post(post_path):
    with open(post_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 
    parts = content.split('---', 2)
    front_matter_str = parts[1].strip()
    body_content = parts[2].strip()

    front_matter = yaml.safe_load(front_matter_str)

    # 
    prompt = f"""
    Translate the following Korean text into English and reformat it into a markdown file for a blog post.
    ...
    Original Korean text:
    ---
    {content}
    """

    print("prompt: \n", prompt)

    # 
    translated_content = call_api(prompt)

    # 
    output_dir = f'./{TARGET_DIR}'
    os.makedirs(output_dir, exist_ok=True)

    with open(os.path.join(output_dir, 'index.md'), 'w', encoding='utf-8') as f:
        f.write(translated_content)

    print(f"Post processed and saved to {output_dir}")

def main():
    if not POST_PATH or not TARGET_DIR:
        print("POST_PATH and TARGET_DIR environment variables are required.")
        return

    print(f"Starting migration for post: {POST_PATH}")
    process_post(POST_PATH)

if __name__ == "__main__":
    main()