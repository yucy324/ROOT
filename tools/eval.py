import re
from Prompt import *

def dict_eval(message):
    judge1 = not any([message.startswith(prefix.lower()) for prefix in REJECT_DICT])
    judge2 = not any([prefix.lower() in message for prefix in REJECT_DICT])
    if judge1:
        return True
    else:
        return False

def eval_meta_llm_response(meta_response):
    lower_meta_response = meta_response.lower()
    d_eval = dict_eval(lower_meta_response)

    if d_eval and meta_response.startswith('[Prompt'):
        attack_prompt = re.findall(r"\[Prompt(?:\s*\d*)?\]:\s*(.*?)(?=\n*\[Prompt(?:\s*\d*)?\]:|\Z)", meta_response.strip(), flags=re.DOTALL | re.IGNORECASE)
        return d_eval, attack_prompt[0]
    else:
        return d_eval, meta_response

def eval_victim_llm_response(harm_prompt, victim_prompt, victim_response, judge_llm):
    system_prompt = ATTACK_RESPONSE_JUDGE_SYSTEM_PROMPT
    user_prompt = f"[TASK]:{harm_prompt}, [PROMPT]:{victim_prompt}, [RESPONSE]:{victim_response}"
    messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}]
    judge_result = judge_llm.response(messages)
    match_rating = re.search(r'Rating:\s*(?:\[\[)?(\d+)(?:\]\])?', judge_result)
    score = int(match_rating.group(1)) if match_rating else 0
    match_reason = re.search(r'Reason:\s*(?:\[\[)?([\s\S]+?)(?:\]\])?\s*$', judge_result)
    experience = match_reason.group(1).strip() if match_reason else ''
    return score, experience

def eval_strategy(experience, strategy, judge_llm):
    system_prompt = STRATEGY_JUDGE_SYSTEM_PROMPT
    strategy_list = [f'Strategy {i+1}: {s}' for i, s in enumerate(strategy)]
    user_prompt = f"[EXPERIENCES]:{experience}, [STRATEGIES]:{strategy_list}"
    messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}]
    judge_result = judge_llm.response(messages)
    scores = []

    pattern = r"\[Strategy (\d+):\s*\{'M':\s*(\d+),\s*'C':\s*(\d+),\s*'E':\s*(\d+)\}\]"
    for m in re.finditer(pattern, judge_result):
        idx, m_score, c_score, e_score = m.groups()
        total = int(m_score) + int(c_score) + int(e_score)
        scores.append(total)
    ids = [i for i, x in enumerate(scores) if x > sum(scores) / len(scores)]
    adopted_strategies = [strategy[i] for i in ids]
    return adopted_strategies