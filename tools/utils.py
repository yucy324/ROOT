import random
import pandas
import os, json

def sample_task_ids(success_task, failure_task, K):
    success_indices = [i for i, s in enumerate(success_task) if s.strip() != '']
    failure_indices = [i for i, f in enumerate(failure_task) if f.strip() != '']

    if not success_indices and not failure_indices:
        return [], []
    elif not success_indices and failure_indices:
        sampled_failure_ids = random.sample(failure_indices, min(K, len(failure_indices)))
        return [], sampled_failure_ids
    elif success_indices and not failure_indices:
        sampled_success_ids = random.sample(success_indices, min(K, len(success_indices)))
        return sampled_success_ids, []
    else:
        sampled_success_ids = random.sample(success_indices, min(K, len(success_indices)))
        sampled_failure_ids = random.sample(failure_indices, min(K, len(failure_indices)))
        return sampled_success_ids, sampled_failure_ids

def merge_tasks(all_TASK, path):
    files = os.listdir(path)
    data_all = {}
    count = 0
    for file in files:
        if file.startswith("iter_"):
            count += 1
            with open(os.path.join(path, file), "r", encoding="utf-8") as f:
                data_all[count] = json.load(f)
    results = []
    for i, task in enumerate(all_TASK):
        found = False  # 用于标记是否已找到任务
        for j in reversed(list(data_all.keys())):
            for item in data_all[j]:
                if item['task'] == task:
                    item['id'] = i
                    results.append(item)
                    found = True
                    break
            if found:
                break
    with open(os.path.join(path, "all_results.json"), "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=4)