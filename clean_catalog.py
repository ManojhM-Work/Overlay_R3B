import re

def clean_catalog():
    filepath = "response_codes_catalog.py"
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    lines = content.splitlines()
    new_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith('"') and stripped.endswith('",'):
            val = stripped[1:-2]
            cleaned_val = val.strip()
            while cleaned_val.endswith("-") or cleaned_val.endswith(" "):
                cleaned_val = cleaned_val.rstrip(" -")
            line = line.replace(f'"{val}",', f'"{cleaned_val}",')
        new_lines.append(line)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write("\n".join(new_lines) + "\n")
    print("Successfully cleaned trailing hyphens and spaces from response_codes_catalog.py!")

if __name__ == "__main__":
    clean_catalog()
