import json
import re

transcript_path = r"C:\Users\grand\.gemini\antigravity\brain\2bbf82b9-c8db-4edf-b6cb-b92d53207906\.system_generated\logs\transcript_full.jsonl"

with open(transcript_path, "r", encoding="utf-8") as f:
    for idx, line in enumerate(f):
        data = json.loads(line)
        content = data.get("content", "")
        if "F-01" in content and "F-12" in content:
            print(f"Match found on line {idx}, length {len(content)}")
            # Print sections describing F-01 to F-12
            lines = content.splitlines()
            for l_idx, l in enumerate(lines):
                if re.search(r"F-0[1-9]|F-1[0-2]", l):
                    print(f"L{l_idx}: {l}")
                    for follow in range(l_idx+1, min(l_idx+15, len(lines))):
                        if lines[follow].startswith("#") or re.search(r"F-0[1-9]|F-1[0-2]", lines[follow]):
                            break
                        print(f"   {lines[follow]}")
