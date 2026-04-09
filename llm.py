import json
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from config import DEEPSEEK_API_KEY, DEEPSEEK_API_BASE, DEEPSEEK_MODEL

# System prompt 告知模型必须输出 JSON
_SYSTEM_PROMPT = (
    "你是一个技术内容创作者，帮助读者了解 GitHub 热门项目。"
    "你必须严格按照 JSON 格式输出，不得包含任何 JSON 以外的内容。"
)

_USER_PROMPT_TEMPLATE = """仓库信息：
- 名称：{name}
- 描述：{description}
- 语言：{language}
- README：{readme}

请生成以下两段内容，以 JSON 格式返回，结构如下：
{{
  "仓库解读": "用口语化、有故事感的方式介绍这个项目：它是什么、解决什么问题、适合谁用。面向非技术读者，200字以内。",
  "快速上手": "结构化介绍：① 核心功能（2-3条）② 上手步骤（2-3步）。面向有一定基础的读者，300字以内。"
}}"""


def _call_api(name: str, description: str, language: str, readme: str) -> dict:
    prompt = _USER_PROMPT_TEMPLATE.format(
        name=name,
        description=description or "暂无描述",
        language=language or "未知",
        readme=readme or description or "暂无描述",
    )
    resp = requests.post(
        f"{DEEPSEEK_API_BASE}/chat/completions",
        headers={
            "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": DEEPSEEK_MODEL,
            "messages": [
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.7,
            "max_tokens": 800,
            "response_format": {"type": "json_object"},
        },
        timeout=60,
    )
    resp.raise_for_status()
    data = resp.json()
    choices = data.get("choices", [])
    if not choices:
        raise ValueError(f"DeepSeek 返回空 choices: {data}")

    raw = choices[0]["message"]["content"]
    parsed = json.loads(raw)
    return {
        "仓库解读": parsed.get("仓库解读", "").strip(),
        "快速上手": parsed.get("快速上手", "").strip(),
    }


def generate_repo_content(name: str, description: str, language: str, readme: str) -> dict:
    """生成仓库解读和快速上手内容（JSON mode），失败重试一次，仍失败返回空字段。"""
    for attempt in range(2):
        try:
            return _call_api(name, description, language, readme)
        except Exception as e:
            print(f"[llm] {name} 第 {attempt + 1} 次调用失败: {e}")
    return {"仓库解读": "", "快速上手": ""}


def generate_repo_content_batch(repos: list[dict]) -> dict[str, dict]:
    """
    并发生成多个仓库的内容，返回 {repo_url: {"仓库解读": ..., "快速上手": ...}} 映射。
    每个 repo dict 需包含 name / description / language / _readme 键。
    """
    results: dict[str, dict] = {}
    with ThreadPoolExecutor(max_workers=8) as executor:
        future_to_url = {
            executor.submit(
                generate_repo_content,
                repo["name"],
                repo["description"],
                repo["language"],
                repo.get("_readme", ""),
            ): repo["url"]
            for repo in repos
        }
        for future in as_completed(future_to_url):
            url = future_to_url[future]
            try:
                results[url] = future.result()
            except Exception as e:
                print(f"[llm] 批量处理异常 {url}: {e}")
                results[url] = {"仓库解读": "", "快速上手": ""}
    return results


def _translate_to_chinese(text: str) -> str:
    """将文本翻译为简体中文，失败时返回原文。"""
    if not text or not text.strip():
        return text
    resp = requests.post(
        f"{DEEPSEEK_API_BASE}/chat/completions",
        headers={
            "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": DEEPSEEK_MODEL,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "你是一名专业翻译，将用户提供的文本翻译为简体中文。"
                        "只输出翻译结果，不添加任何解释或额外内容。"
                        "若文本已是简体中文，则原样返回。"
                    ),
                },
                {"role": "user", "content": text},
            ],
            "temperature": 0.3,
            "max_tokens": 300,
        },
        timeout=30,
    )
    resp.raise_for_status()
    choices = resp.json().get("choices", [])
    if not choices:
        return text
    return choices[0]["message"]["content"].strip()


def translate_news_items(items: list) -> list:
    """
    并发将新闻条目的标题和摘要翻译为简体中文，返回翻译后的新列表。
    每个 item 为 NewsItem TypedDict（含 title/summary 字段）。
    """
    def _translate_item(item):
        translated = dict(item)
        try:
            translated["title"] = _translate_to_chinese(item.get("title", ""))
        except Exception as e:
            print(f"[llm] 翻译标题失败: {e}")
        try:
            translated["summary"] = _translate_to_chinese(item.get("summary", ""))
        except Exception as e:
            print(f"[llm] 翻译摘要失败: {e}")
        return translated

    with ThreadPoolExecutor(max_workers=8) as executor:
        return list(executor.map(_translate_item, items))
