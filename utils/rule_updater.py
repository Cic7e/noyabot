import json
import os
import re
from collections import defaultdict

import aiohttp
import aiofiles

GENERAL_RULES_URL = "https://raw.githubusercontent.com/AdguardTeam/AdguardFilters/master/TrackParamFilter/sections/general_url.txt"
SPECIFIC_RULES_URL = "https://raw.githubusercontent.com/AdguardTeam/AdguardFilters/master/TrackParamFilter/sections/specific.txt"
RULES_PATH = "data/rules.json"

async def update_rules_from_source():
    raw_rules_text = ""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(GENERAL_RULES_URL) as response:
                response.raise_for_status()
                raw_rules_text += await response.text() + "\n"
            async with session.get(SPECIFIC_RULES_URL) as response:
                response.raise_for_status()
                raw_rules_text += await response.text()
    except aiohttp.ClientError as e:
        print(f"Error: Could not download rules - aborting update. {e}")
        return None
    parsed_rules = defaultdict(set)
    lines = raw_rules_text.splitlines()
    valid_param_regex = re.compile(r'^[a-zA-Z0-9_-]+$')
    for line in lines:
        if '$removeparam=' not in line:
            continue
        try:
            params_str = line.split('$removeparam=')[1]
            potential_params = params_str.split('|')
            cleaned_params = set()
            for param in potential_params:
                clean_param = param.split(',')[0].strip()
                if clean_param.startswith('/') and clean_param.endswith('/'):
                    continue
                if valid_param_regex.match(clean_param):
                    cleaned_params.add(clean_param)
            if not cleaned_params:
                continue
            if line.startswith('||'):
                match = re.search(r'^\|\|([^\^/$]+)', line)
                if match:
                    domain = match.group(1).strip()
                    if '*' not in domain and 'http' not in domain:
                        parsed_rules[domain].update(cleaned_params)
            else:
                parsed_rules["GENERAL"].update(cleaned_params)
        except Exception:
            continue
    final_rules = {domain: sorted(list(params)) for domain, params in parsed_rules.items()}
    specific_rule_count = len(final_rules) - 1 if "GENERAL" in final_rules else len(final_rules)
    general_rule_count = len(final_rules.get("GENERAL", []))
    try:
        os.makedirs("data", exist_ok=True)
        async with aiofiles.open(RULES_PATH, 'w', encoding='utf-8') as f:
            await f.write(json.dumps(final_rules, indent=2))
        print(f"Successfully saved rules to {RULES_PATH}.")
    except IOError as e:
        print(f"Error: Could not save rules to {RULES_PATH}. {e}")
        return None
    return {"general": general_rule_count, "specific": specific_rule_count}