
import json
import re

def clean_json(text):
    """
    Clean and extract valid JSON from AI response.
    """
    text = text.strip()
    
    # 1. Remove Markdown code blocks
    if "```" in text:
        pattern = r"```(?:json|JSON)?\s*([\s\S]*?)\s*```"
        match = re.search(pattern, text)
        if match:
            text = match.group(1).strip()
            
    # 2. Try direct parse
    try:
        return json.loads(text)
    except:
        pass

    # 3. Fix common errors
    # Remove trailing commas inside objects/arrays
    text = re.sub(r",\s*}", "}", text)
    text = re.sub(r",\s*]", "]", text)
    
    # Check for truncation (unterminated string) - hard to fix perfectly, 
    # but we can try to find the last valid object closure.
    # For now, let's just try to parse.
    
    try:
        return json.loads(text)
    except:
        pass
        
    # 4. Extract first valid JSON object/array
    # Find the matching brace for the first { or [
    stack = []
    start_index = -1
    
    for i, char in enumerate(text):
        if char == '{' or char == '[':
            if not stack:
                start_index = i
            stack.append(char)
        elif char == '}' or char == ']':
            if stack:
                last = stack[-1]
                if (char == '}' and last == '{') or (char == ']' and last == '['):
                    stack.pop()
                    if not stack:
                        # Found a complete block
                        candidate = text[start_index:i+1]
                        try:
                            return json.loads(candidate)
                        except:
                            pass
    
    return None

# Test cases
cases = [
    # 1. Valid JSON
    '{"a": 1}',
    # 2. Markdown wrapped
    'Here is the JSON:\n```json\n{"a": 1}\n```',
    # 3. Trailing comma
    '{"a": 1,}',
    # 4. Nested structure
    '{"a": {"b": 2}}',
    # 5. Surrounded by text
    'Output: {"a": 1} End.'
]

print("Running tests...")
for i, case in enumerate(cases):
    print(f"Case {i+1}: {case[:20]}... -> ", end="")
    res = clean_json(case)
    if res:
        print(f"Success: {res}")
    else:
        print("Failed")
