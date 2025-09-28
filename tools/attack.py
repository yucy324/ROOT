from Prompt import *
import re
from tools.eval import dict_eval

def meta_prompt_generate(task, meta_system_prompt=None):
    if meta_system_prompt is None:
        meta_system_prompt = META_SYSTEM_PROMPT
    system_prompt = meta_system_prompt
    user_prompt = f'[TASK]: {task}'

    meta_prompt = [{"role": "system", "content": system_prompt},
                   {"role": "user", "content": user_prompt}]

    return meta_prompt

def attack_prompt_generate(task):
    user_prompt = f'[TASK]: {task}'
    attack_prompt = [{"role": "user", "content": user_prompt}]
    return attack_prompt

def generate_strategy(task, attack_prompt, attack_response, meta_system_prompt, experience, strategy_num, strategy_generator_llm):
    if meta_system_prompt is None:
        meta_system_prompt = META_SYSTEM_PROMPT
    assert len(task) == len(attack_prompt) == len(attack_response)
    example_list = {}
    for i in range(len(task)):
        example = {}
        example['TASK'] = task[i]
        example['ATTACK_PROMPT'] = attack_prompt[i]
        example['ATTACK_RESPONSE'] = attack_response[i]
        example_list[f"EXAMPLE {i+1}: "] = example
    system_prompt = GENERATE_STRATEGY_SYSTEM_PROMPT
    user_prompt = f"[META_PROMPT]: {meta_system_prompt}, [EXAMPLES]: {example_list}, [EXPERIENCES]: {experience}, [NUM]:{strategy_num}"
    messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}]
    strategy_result = strategy_generator_llm.response(messages)

    lower_meta_response = strategy_result.lower()
    d_eval = dict_eval(lower_meta_response)
    if d_eval:
        pattern = r"\[Strategy\s*\d+\]:\s*(.*?)(?=\n\[Strategy\s*\d+\]:|\Z)"
        strategy_list = [item.strip() for item in re.findall(pattern, strategy_result, flags=re.DOTALL)]
    else:
        strategy_list = []
    return strategy_list, example_list

def optimize_meta_prompt(meta_system_prompt, examples, experiences, strategies, strategy_generator_llm):
    system_prompt = OPTIMIZE_META_PROMPT_SYSTEM_PROMPT
    if meta_system_prompt is None:
        meta_system_prompt = META_SYSTEM_PROMPT
    user_prompt = f"[META_PROMPT]: {meta_system_prompt}, [EXAMPLES]: {examples}, [EXPERIENCES]: {experiences}, [STRATEGIES]: {strategies}"
    messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}]
    strategy_result = strategy_generator_llm.response(messages)
    return strategy_result