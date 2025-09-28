import time
from openai import OpenAI

class LLM():
    def __init__(self, model_id, temperature=0, retry_time=1000, failed_sleep_time=1, round_sleep_time=1, type=0) -> None:
        self.model_id = model_id
        self.temperature = temperature
        self.retry_time = retry_time
        self.failed_sleep_time = failed_sleep_time
        self.round_sleep_time = round_sleep_time
        self.type = type

    def QwenCompletion(self, messages, base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"):
        api_keys="sk-XXX"
        if base_url is None:
            client = OpenAI(
                api_key=api_keys,
            )
        else:
            client = OpenAI(
                api_key=api_keys,
                base_url=base_url
            )
        response = None
        try:
            response = client.chat.completions.create(
                model=self.model_id,
                messages=messages,
                temperature=self.temperature,
                extra_body={"enable_thinking": False}
            )
        except Exception as e:
            print(e)
            for retry_time in range(1, self.retry_time + 1):
                print(f"{self.model_id} Retry {retry_time}")
                time.sleep(self.failed_sleep_time * retry_time)
                try:
                    response = client.chat.completions.create(
                        model=self.model_id,
                        messages=messages,
                        temperature=self.temperature,
                        extra_body={"enable_thinking": False}
                    )
                    break
                except Exception as error:
                    print(f"Error occurred: {error}, continue retrying...")
                    continue
            if retry_time == self.retry_time:
                print("Failed to get response from OpenAI API.")

        if response and hasattr(response, "choices") and response.choices:
            model_output = response.choices[0].message.content.strip()
        else:
            model_output = "I'm sorry"
        time.sleep(self.round_sleep_time)

        return model_output

    def OpenRouterCompletion(self, messages, base_url="https://openrouter.ai/api/v1"):
        api_key = "sk-or-XXX",
        if base_url is None:
            client = OpenAI(
                api_key=api_key,
            )
        else:
            client = OpenAI(
                api_key=api_key,
                base_url=base_url
            )
        response = None
        try:
            response = client.chat.completions.create(
                model=self.model_id,
                messages=messages,
                temperature=self.temperature
            )
        except Exception as e:
            print(e)
            for retry_time in range(1, self.retry_time + 1):
                print(f"{self.model_id} Retry {retry_time}")
                time.sleep(self.failed_sleep_time * retry_time)
                try:
                    response = client.chat.completions.create(
                        model=self.model_id,
                        messages=messages,
                        temperature=self.temperature
                    )
                    break
                except Exception as error:
                    print(f"Error occurred: {error}, continue retrying...")
                    continue

        if response and hasattr(response, "choices") and response.choices:
            model_output = response.choices[0].message.content.strip()
        else:
            model_output = "I'm sorry"
        time.sleep(self.round_sleep_time)

        return model_output

    def response(self, messages):
        openrouter_models = [
        "openai/gpt-3.5-turbo",
        "openai/gpt-4-turbo",
        "openai/gpt-4",
        "openai/gpt-4o-2024-08-06",
        "openai/gpt-4o-mini-2024-07-18",
        "anthropic/claude-3.5-sonnet-20240620",
        "anthropic/claude-sonnet-4",
        "meta-llama/llama-3.1-405b-instruct",
        "mistralai/mixtral-8x22b-instruct",
        "meta-llama/llama-3.3-70b-instruct:free",
        "anthropic/claude-sonnet-4",
        "qwen/qwen3-235b-a22b",
        "deepseek/deepseek-r1-0528",
        "deepseek/deepseek-r1-0528:free",
        "meta-llama/llama-2-13b-chat",
        "mistralai/mistral-small-3.2-24b-instruct:free",
        "meta-llama/llama-guard-2-8b",
        "meta-llama/llama-guard-3-8b",
        "meta-llama/llama-guard-4-12b",
         ]
        if self.type == 1 and self.model_id in openrouter_models:
            llm_output = self.OpenRouterCompletion(messages)
        else:
            if "qwen" in self.model_id:
                llm_output = self.QwenCompletion(messages)
            else:
                raise NameError("Unknown Chatbot {}, please add the implementation.".format(self.model_id))

        return llm_output
