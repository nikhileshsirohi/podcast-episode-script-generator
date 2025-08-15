from src.generation.gemini_client import configure_gemini
import google.generativeai as genai

# Step 1: Configure Gemini with API key
configure_gemini()

# Step 2: Pick the model
model = genai.GenerativeModel("gemini-1.5-flash")

# Step 3: Create a sample prompt
prompt = """
You are a podcast script writer.
Turn the following text into a short podcast episode with
an intro, two segments, and an outro.

Text:
India won the cricket match against England after a thrilling last over chase.
Virat Kohli scored 85 runs, leading the team to victory.
The stadium was packed with cheering fans.
"""

# Step 4: Send request
response = model.generate_content(prompt)

# Step 5: Print result
print("\n--- Generated Podcast Script ---\n")
print(response.text)