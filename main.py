import os, time
import json
import pandas
import argparse

from Prompt import *
from llm import LLM
from tools.attack import meta_prompt_generate, attack_prompt_generate, generate_strategy, optimize_meta_prompt
from tools.eval import eval_meta_llm_response, eval_victim_llm_response, eval_strategy, dict_eval
from tools.utils import sample_task_ids, merge_tasks

def main():
    parser = argparse.ArgumentParser()

    parser.add_argument('--iter_num', type=int, default=2, help="number of iterations")

    parser.add_argument("--meta_llm", type=str, default="qwen-max-0428", help="name of meta LLM")
    parser.add_argument("--victim_llm", type=str, default="openai/gpt-3.5-turbo", help="name of victim LLM")
    parser.add_argument("--judge_llm", type=str, default="openai/gpt-4", help="judge attack_response score")
    parser.add_argument("--optimize_llm", type=str, default="qwen-max-0428")

    parser.add_argument("--retry_time", type=int, default=3, help="max retry time of failed API calling")
    parser.add_argument("--failed_sleep_time", type=int, default=60, help="sleep time of failed API calling")
    parser.add_argument("--round_sleep_time", type=int, default=1, help="sleep time of round")
    parser.add_argument("--temperature", type=float, default=0, help="temperature of victim LLM")

    parser.add_argument("--data_name", type=str, default="advbench", choices=["advbench", "advbench_subset"],
                        help="benchmark name")
    parser.add_argument("--output_dict", type=str, default="result", help="output path")

    parser.add_argument("--case_num", type=int, default=5, help="cases used for summary")
    parser.add_argument("--strategy_num", type=int, default=3, help="strategy for experience of the cases")

    parser.add_argument("--type", default=1, type=int)
    args = parser.parse_args()

    if args.data_name=='advbench':
        args.data_path = "data/harmful_behaviors.csv"
    elif args.data_name=='advbench_subset':
        args.data_path = "data/harmful_behaviors_subset.csv"
    else:
        raise NameError("Unknown Benchmark {}, please add the implementation.".format(args.data_name))

    meta_llm = LLM(model_id=args.meta_llm,
                   temperature=args.temperature,
                   retry_time=args.retry_time,
                   failed_sleep_time=args.failed_sleep_time,
                   round_sleep_time=args.round_sleep_time,
                   type=args.type)

    victim_llm = LLM(model_id=args.victim_llm,
               temperature=args.temperature,
               retry_time=args.retry_time,
               failed_sleep_time=args.failed_sleep_time,
               round_sleep_time=args.round_sleep_time,
               type=args.type)

    judge_llm = LLM(model_id=args.judge_llm,
               temperature=args.temperature,
               failed_sleep_time=args.failed_sleep_time,
               retry_time=3,
               type=args.type)
    optimize_llm = LLM(model_id=args.optimize_llm,
                       temperature=args.temperature,
                       failed_sleep_time=args.failed_sleep_time,
                       retry_time=3, type=args.type)

    adv_bench = pandas.read_csv(args.data_path)
    all_TASK = adv_bench["goal"]
    ori_all_TASK = all_TASK.copy()

    time_str = time.strftime("%Y%m%d-%H%M%S")
    output_file_name = f'meta_llm_{args.meta_llm}_victim_llm_{args.victim_llm}_{time_str}'
    if '/' in output_file_name or ':' in output_file_name:
        output_file_name = output_file_name.replace("/", "-")
        output_file_name = output_file_name.replace(":", "-")
    pck_path = os.path.join(args.output_dict, output_file_name)
    if not os.path.exists(pck_path):
        os.makedirs(pck_path)
    llm_info = f'meta_llm: {args.meta_llm}, victim_llm: {args.victim_llm}, judge_llm: {args.judge_llm}, optimize_llm: {args.optimize_llm}\n'
    with open(os.path.join(pck_path, "info.txt"), "w", encoding='utf-8') as f:
        f.write(llm_info + '\n')

    with open(os.path.join(pck_path, "save.txt"), "w", encoding='utf-8') as f:
        f.write('template info \n')

    meta_system_prompt = None
    best_asr = 0
    iter_count = 0
    while iter_count < args.iter_num:
        print("Iteration {}/{}".format(iter_count, args.iter_num))
        iter_count += 1

        meta_response_llm_success_count = 0
        meta_response_dict_success_count = 0
        attack_response_llm_success_count = 0
        attack_response_dict_success_count = 0

        success_count = 0
        success_task = []
        success_attack_prompt = []
        success_attack_response = []
        success_attack_experience = []
        failure_count = 0
        failure_task = []
        failure_attack_prompt = []
        failure_attack_response = []
        failure_attack_experience = []
        failure_meta_dict_eval = []
        failure_attack_dict_eval = []

        for id, task in enumerate(all_TASK):
            print("Round {}: {}".format(id, task))
            meta_attack_prompt = meta_prompt_generate(task, meta_system_prompt)
            meta_response = meta_llm.response(meta_attack_prompt)

            meta_dict_eval, attack_prompt = eval_meta_llm_response(meta_response)
            meta_response_dict_success_count += int(meta_dict_eval)
            if meta_dict_eval and attack_prompt is not None:
                meta_response_llm_success_count += 1
                attack_message = attack_prompt_generate(attack_prompt)
                attack_response = victim_llm.response(attack_message)
                if dict_eval(attack_response.lower()):
                    attack_response_dict_success_count += 1
                    victim_response_score, victim_response_experience = eval_victim_llm_response(task, attack_prompt, attack_response, judge_llm)
                    print("victim_response_score: ", victim_response_score)
                    if victim_response_score == 1:
                        attack_response_llm_success_count += 1
                        success_count += 1
                        success_task.append(task)
                        success_attack_prompt.append(attack_prompt)
                        success_attack_response.append(attack_response)
                        success_attack_experience.append(victim_response_experience)
                    else:
                        failure_count += 1
                        failure_task.append(task)
                        failure_attack_prompt.append(attack_prompt)
                        failure_attack_response.append(attack_response)
                        failure_attack_experience.append(victim_response_experience)
                        failure_meta_dict_eval.append(True)
                        failure_attack_dict_eval.append(True)
                else:
                    failure_count += 1
                    failure_task.append(task)
                    failure_attack_prompt.append(attack_prompt)
                    failure_attack_response.append(attack_response)
                    failure_attack_experience.append('')
                    failure_meta_dict_eval.append(meta_dict_eval)
                    failure_attack_dict_eval.append(False)
            else:
                failure_count += 1
                failure_task.append(task)
                failure_attack_prompt.append(attack_prompt)
                failure_attack_response.append('')
                failure_attack_experience.append('')
                failure_meta_dict_eval.append(meta_dict_eval)
                failure_attack_dict_eval.append(False)
            if id % 10 == 0:
                with open(os.path.join(pck_path, "save.txt"), "a", encoding='utf-8') as f:
                    f.write(f"success attack_prompt: {success_attack_prompt}\n")
                    f.write(f"failure attack_prompt: {failure_attack_prompt}\n")
                    f.write(f"success attack_response: {success_attack_response}\n")
                    f.write(f"failure attack_response: {failure_attack_response}\n")
                    f.write(f"success attack_experience: {success_attack_experience}\n")
                    f.write(f"failure attack_experience: {failure_attack_experience}\n")
                    f.write(f"success meta_dict_eval: {meta_response_dict_success_count}\n")
                    f.write(f"failure meta_dict_eval: {len(failure_meta_dict_eval)}\n")
                    f.write(f"success attack_dict_eval: {attack_response_dict_success_count}\n")
                    f.write(f"failure attack_dict_eval: {len(failure_attack_dict_eval)}\n")
                    f.write(f"success count: {success_count}\n")
                    f.write(f"failure count: {failure_count}\n")
                    f.write(f"meta_response_llm_success_count: {meta_response_llm_success_count}\n")
                    f.write(f"attack_response_llm_success_count: {attack_response_llm_success_count}\n")
                    f.write(f"meta_response_dict_success_count: {meta_response_dict_success_count}\n")
                    f.write(f"attack_response_dict_success_count: {attack_response_dict_success_count}\n")

        if iter_count < args.iter_num:
            selected_success_ids, selected_failure_ids = sample_task_ids(success_attack_experience, failure_attack_experience, args.case_num)

            selected_success_task = [success_task[i] for i in selected_success_ids]
            selected_success_attack_prompt = [success_attack_prompt[i] for i in selected_success_ids]
            selected_success_attack_response = [success_attack_response[i] for i in selected_success_ids]
            selected_success_attack_experience = [success_attack_experience[i] for i in selected_success_ids]

            selected_failure_task = [failure_task[i] for i in selected_failure_ids]
            selected_failure_attack_prompt = [failure_attack_prompt[i] for i in selected_failure_ids]
            selected_failure_attack_response = [failure_attack_response[i] for i in selected_failure_ids]
            selected_failure_attack_experience = [failure_attack_experience[i] for i in selected_failure_ids]

            tasks = selected_success_task + selected_failure_task
            attack_prompts = selected_success_attack_prompt + selected_failure_attack_prompt
            attack_responses = selected_success_attack_response + selected_failure_attack_response
            experiences = selected_success_attack_experience + selected_failure_attack_experience

            strategies, examples = generate_strategy(tasks, attack_prompts, attack_responses, meta_system_prompt, experiences, args.strategy_num, optimize_llm)

            adopted_strategies = eval_strategy(experiences, strategies, optimize_llm)

            meta_system_prompt = optimize_meta_prompt(meta_system_prompt, examples, experiences, adopted_strategies, optimize_llm)

            with open(os.path.join(pck_path, "info.txt"), "a", encoding='utf-8') as f:
                f.write(f"iter_{iter_count}\n Meta_Prompt: {meta_system_prompt}\n" + '\n')

        all_count = len(all_TASK)
        meta_asr_llm = meta_response_llm_success_count / all_count * 100
        meta_asr_dict = meta_response_dict_success_count / all_count * 100
        attack_asr_llm = attack_response_llm_success_count / all_count * 100
        attack_asr_dict = attack_response_dict_success_count / all_count * 100
        if best_asr < attack_asr_llm:
            best_asr = attack_asr_llm
        metrics_dict = {"Best-ATTACK_ASR-LLM": best_asr, "META_ASR-LLM": meta_asr_llm, "META_ASR-DICT": meta_asr_dict, "ATTACK_ASR-LLM": attack_asr_llm, "ATTACK_ASR-DICT": attack_asr_dict}
        print(metrics_dict)

        result_dict_list = []
        for idx, task in enumerate(all_TASK):
            result_dict = {}
            result_dict['id'] = idx
            result_dict['task'] = task
            if task in success_task:
                id = success_task.index(task)
                result_dict['meta_response'] = success_attack_prompt[id]
                result_dict['attack_response'] = success_attack_response[id]
                result_dict['meta_dict_eval'] = True
                result_dict['attack_response_dict_eval'] = True
                result_dict['attack_response_score'] = 1
            elif task in failure_task:
                id = failure_task.index(task)
                result_dict['meta_response'] = failure_attack_prompt[id]
                result_dict['attack_response'] = failure_attack_response[id]
                result_dict['meta_dict_eval'] = failure_meta_dict_eval[id]
                result_dict['attack_response_dict_eval'] = failure_attack_dict_eval[id]
                result_dict['attack_response_score'] = 0
            result_dict_list.append(result_dict)

        with open(os.path.join(pck_path, f"iter_{iter_count}.json"), 'w', encoding='utf-8') as f:
            json.dump(result_dict_list, f, ensure_ascii=False, indent=4)

        if len(failure_task) == 0:
            break
        else:
            all_TASK = pandas.Series(failure_task).copy()
    # merge all cases
    merge_tasks(ori_all_TASK, pck_path)

if __name__ == '__main__':
    main()