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
            "max_tokens": 600,
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


def translate_news_items(items: list) -> list:
    """
    批量将新闻条目的标题和摘要翻译为简体中文（单次 API 调用），返回翻译后的新列表。
    每个 item 为 NewsItem TypedDict（含 title/summary 字段）。
    """
    if not items:
        return items

    # 构造待翻译的结构化数组
    payload = [
        {"i": i, "title": item.get("title", ""), "summary": item.get("summary", "")}
        for i, item in enumerate(items)
    ]

    try:
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
                            "你是一名专业翻译。用户给你一个 JSON 对象，其中 items 字段是数组，"
                            "每个元素包含 i（索引）、title、summary 字段。"
                            "将所有 title 和 summary 翻译为简体中文，已是简体中文的保持不变。"
                            "严格按如下格式返回，不添加任何多余内容：\n"
                            '{"items": [{"i": 0, "title": "...", "summary": "..."}, ...]}'
                        ),
                    },
                    {"role": "user", "content": json.dumps({"items": payload}, ensure_ascii=False)},
                ],
                "temperature": 0.3,
                "max_tokens": 6000,
                "response_format": {"type": "json_object"},
            },
            timeout=120,
        )
        resp.raise_for_status()
        raw = resp.json()["choices"][0]["message"]["content"]
        translated_list = json.loads(raw).get("items", [])

        # 按索引回填
        index_map = {entry["i"]: entry for entry in translated_list}
        result = []
        for i, item in enumerate(items):
            new_item = dict(item)
            if i in index_map:
                new_item["title"] = index_map[i].get("title", item.get("title", ""))
                new_item["summary"] = index_map[i].get("summary", item.get("summary", ""))
            result.append(new_item)
        return result

    except Exception as e:
        print(f"[llm] 批量翻译失败: {e}，返回原文")
        return list(items)

