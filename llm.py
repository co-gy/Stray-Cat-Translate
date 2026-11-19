from functools import partial
from openai import OpenAI

class LLM:
    def __init__(self, base_url: str, api_key: str, model: str):
        self.client = OpenAI(
            base_url=base_url,
            api_key=api_key,
            default_headers={"User-Agent": "llm-translate/1.0"}
        )
        self.model = model
        # self.ping()

    def ping(self):
        self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "user",
                    "content": "hello"
                }
            ]
        )

    def __call__(self, prompt: str, buffer_size:int = 1, print_func=None) -> str:
        if print_func is None:
            print_func = partial(print, end="", flush=True)

        resp = ""
        buffer = ""

        response = self.client.chat.completions.create(
            model=self.model,
            stream=True,
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )
        total_usage = None
        for r in response:
            if r.usage is not None:
                total_usage = r.usage.total_tokens
            if len(r.choices) > 0 and r.choices[0].delta.content is not None:
                chunk = r.choices[0].delta.content
                buffer += chunk
                resp += chunk
                if len(buffer)>buffer_size:
                    print_func(buffer)
                    buffer = ""
        if buffer:
            print_func(buffer)
        resp = resp.strip()
        total_usage = total_usage or int((len(prompt)+len(resp))/2.5)
        return resp, total_usage
