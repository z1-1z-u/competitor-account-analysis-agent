import csv
import io
import sqlite3
import json
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

REQUIRED = {"account_id", "account_name", "account_positioning", "post_id", "title", "content", "hashtags", "publish_time", "likes", "collects", "comments", "is_viral"}
DB_PATH = Path(__file__).with_name("reviews.db")


def number(value: Any) -> int:
    try:
        return int(float(str(value).replace(",", "").strip()))
    except (TypeError, ValueError):
        return 0


def read_csv(source: Any) -> list[dict[str, Any]]:
    if isinstance(source, (str, Path)):
        raw = Path(source).read_bytes()
    else:
        raw = source.getvalue() if hasattr(source, "getvalue") else source.read()
    text = None
    for encoding in ("utf-8-sig", "gb18030", "gbk"):
        try:
            text = raw.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    if text is None:
        raise ValueError("CSV 编码无法识别，请另存为 UTF-8 编码")
    rows = list(csv.DictReader(io.StringIO(text)))
    if not rows:
        raise ValueError("CSV 中没有数据")
    missing = REQUIRED - set(rows[0])
    if missing:
        raise ValueError("缺少字段：" + ", ".join(sorted(missing)))
    for row in rows:
        row["likes"] = number(row["likes"])
        row["collects"] = number(row["collects"])
        row["comments"] = number(row["comments"])
        row["engagement"] = row["likes"] + row["collects"] + row["comments"]
        row["is_viral"] = str(row["is_viral"]).lower() in {"true", "1", "yes", "是"}
        row.setdefault("target_audience", "")
        row.setdefault("content_type", "")
        row.setdefault("notes", "")
    return rows


def read_feedback(source: Any) -> list[dict[str, Any]]:
    raw = source.getvalue() if hasattr(source, "getvalue") else source.read()
    text = None
    for encoding in ("utf-8-sig", "gb18030", "gbk"):
        try:
            text = raw.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    if text is None:
        raise ValueError("反馈 CSV 编码无法识别")
    rows = list(csv.DictReader(io.StringIO(text)))
    required = {"title", "likes", "collects", "comments"}
    missing = required - set(rows[0] if rows else [])
    if missing:
        raise ValueError("反馈 CSV 缺少字段：" + ", ".join(sorted(missing)))
    return rows


def analyze(posts: list[dict[str, Any]], own_positioning: str) -> dict[str, Any]:
    accounts = {}
    for post in posts:
        accounts.setdefault(post["account_id"], []).append(post)
    profiles = []
    for account_id, items in accounts.items():
        best = max(items, key=lambda x: x["engagement"])
        avg = sum(x["engagement"] for x in items) / len(items)
        types = sorted({x.get("content_type", "") for x in items if x.get("content_type")})
        profiles.append({"account_id": account_id, "name": best["account_name"], "positioning": best["account_positioning"], "posts": len(items), "average": avg, "best": best["title"], "types": "、".join(types)})
    viral = [p for p in posts if p["is_viral"]]
    common_tags = {}
    for post in viral or posts:
        for tag in post["hashtags"].replace("|", " ").split():
            if tag.startswith("#"): common_tags[tag] = common_tags.get(tag, 0) + 1
    high_posts = sorted(viral or posts, key=lambda item: item["engagement"], reverse=True)
    example = high_posts[0]
    example_title = example["title"]
    example_tags = " ".join(example["hashtags"].split()[:4])
    example_type = example.get("content_type") or "经验/推荐类"
    mechanisms = [
        {"可借鉴机制": "标题先给结果或情绪，再补充主题", "数据证据": f"高表现样本：{example_title}", "为什么有效": "用户在首屏即可判断内容价值或情绪方向", "不能照搬的表达": f"不能复制原标题中的书名、金句和情绪化措辞：{example_title}", "建议改写": "保留结果导向，替换为我方用户、场景和原创结论"},
        {"可借鉴机制": f"{example_type}的具体细节结构", "数据证据": f"样本正文长度约 {len(example['content'])} 字，互动 {example['engagement']:,}", "为什么有效": "具体细节让内容更可信，也更容易被收藏", "不能照搬的表达": "不能复制原文的故事顺序、人物经历、书摘和案例细节", "建议改写": "使用自己的经历、测试过程或公开可核验资料重新组织"},
        {"可借鉴机制": "垂直标签与泛兴趣标签组合", "数据证据": f"样本标签：{example_tags or '未提供标签'}", "为什么有效": "同时覆盖精准人群和更大的兴趣范围", "不能照搬的表达": f"不能整组复制标签、账号话题词或品牌词：{example_tags or '原标签组合'}", "建议改写": "保留主题方向，根据我方目标用户重新选择标签"},
        {"可借鉴机制": "信息价值与情绪价值结合", "数据证据": "高表现样本同时包含观点、细节和个人感受", "为什么有效": "既帮助用户解决问题，也促使用户产生共鸣和评论", "不能照搬的表达": "不能复制原文金句、书摘、品牌、图片和固定口头禅", "建议改写": "保留情绪功能，但改用我方账号真实表达和原创素材"},
    ]
    topic_summary = []
    for index, post in enumerate(high_posts[:8], 1):
        content_type = post.get("content_type") or "综合分享"
        audience = post.get("target_audience") or post.get("account_positioning") or "账号目标用户"
        topic_summary.append({
            "选题编号": f"T{index}",
            "高表现选题": infer_topic(post),
            "内容类型": content_type,
            "目标需求": f"满足{audience}对信息、方法或情绪共鸣的需求",
            "数据表现": f"互动 {post['engagement']:,}（赞 {post['likes']:,} / 藏 {post['collects']:,} / 评 {post['comments']:,}）",
            "可借鉴选题机制": f"围绕‘{content_type}’提供具体价值，并用真实细节支撑观点",
            "不能照搬": "具体书目、人物经历、故事细节、原文观点和图片素材",
            "我方改写方向": f"将该选题机制迁移到‘{own_positioning or '我方账号定位'}’的真实用户场景"
        })
    risks = ["不要复制对标账号的原文、具体案例、独家经历、图片和固定口头禅。", "书名、数据、品牌和引用需要人工核验来源。"]
    opportunities = [f"围绕你的定位“{own_positioning or '待填写'}”，把对标账号的有效结构改造成自己的案例和表达。", "在共同主题之外，增加一个对标账号没有覆盖的细分人群或使用场景。", "保留可执行清单结构，但使用自己的图片、经历和结论。"]
    plans = []
    title_patterns = {
        "问题解决": "如果你也遇到这个问题，先试试这3步",
        "场景实测": "我用一周时间验证了：{theme}到底有没有用",
        "清单对比": "围绕{theme}，这4种做法怎么选？",
        "误区纠正": "关于{theme}，最容易被忽略的一个误区",
        "互动征集": "想请大家一起讨论：你会怎么处理{theme}？",
    }
    theme = own_positioning or "这个主题"
    for i, angle in enumerate(title_patterns, 1):
        plan = {"plan_id": f"P{i}", "title": title_patterns[angle].format(theme=theme), "angle": angle, "hook": f"从{angle}角度切入，先提出目标用户熟悉的场景，再给出明确结果。", "content_keywords": f"{theme}、{angle}、真实场景、具体方法、适用边界", "structure": "真实场景 -> 关键问题 -> 3 个具体方法 -> 适用边界 -> 互动提问", "image_suggestion": "使用自己的场景图或原创信息卡片", "cta": "你遇到过类似情况吗？欢迎分享你的方法。", "risk": "使用原创案例和图片，避免复刻某个对标账号的标题"}
        plans.append(plan)
    similarity = check_similarity(plans, posts)
    return {"profiles": profiles, "common_tags": "、".join(sorted(common_tags, key=common_tags.get, reverse=True)[:8]), "topic_summary": topic_summary, "mechanisms": mechanisms, "risks": risks, "opportunities": opportunities, "plans": plans, "similarity": similarity}


def infer_topic(post: dict[str, Any]) -> str:
    # Describe the topic from structured fields; this is not a semantic model call.
    title = post.get("title", "").strip()
    content_type = post.get("content_type", "").strip()
    positioning = post.get("account_positioning", "").strip()
    if content_type and title:
        return f"{content_type}：{title}所对应的具体问题或主题"
    if title:
        return f"围绕‘{title}’的用户需求与内容分享"
    return positioning or "未命名选题"


def check_similarity(plans: list[dict[str, Any]], posts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    results = []
    for plan in plans:
        plan_text = plan["title"] + " " + plan["hook"] + " " + plan["content_keywords"] + " " + plan["structure"]
        def score_post(post: dict[str, Any]) -> float:
            source_text = post["title"] + " " + post["content"][:500] + " " + post["hashtags"] + " " + post.get("content_type", "")
            return SequenceMatcher(None, plan_text, source_text).ratio()
        best = max(posts, key=score_post)
        score = score_post(best)
        level = "高风险" if score >= 0.75 else "中风险" if score >= 0.45 else "低风险"
        keyword_score = SequenceMatcher(None, plan["content_keywords"], best.get("content", "")[:500] + " " + best.get("hashtags", "")).ratio()
        structure_score = SequenceMatcher(None, plan["structure"], best.get("content", "")[:500]).ratio()
        results.append({"plan_id": plan["plan_id"], "生成标题": plan["title"], "内容关键词": plan["content_keywords"], "对标内容关键词/片段": (best.get("content", "")[:100] + " " + best.get("hashtags", "")), "最相似对标账号": best["account_name"], "最相似对标标题": best["title"], "标题与内容综合相似度": f"{score:.1%}", "关键词相似度": f"{keyword_score:.1%}", "结构相似度": f"{structure_score:.1%}", "风险等级": level, "建议": "重写关键词、切入角度、案例和标题" if level != "低风险" else "可继续人工核验"})
    return results


def compare_own_content(own: dict[str, str], posts: list[dict[str, Any]]) -> dict[str, Any]:
    benchmark = max(posts, key=lambda p: p["engagement"])
    fields = [("标题", own.get("title", ""), benchmark.get("title", "")), ("正文", own.get("content", ""), benchmark.get("content", "")), ("标签", own.get("hashtags", ""), benchmark.get("hashtags", ""))]
    rows = []
    for name, left, right in fields:
        score = SequenceMatcher(None, left, right).ratio() if left and right else 0
        risk = "高风险" if score >= .75 else "中风险" if score >= .45 else "低风险"
        rows.append({"比较维度": name, "我方内容": left[:180], "最相似对标内容": right[:180], "相似度": f"{score:.1%}", "风险": risk})
    return {"benchmark": benchmark, "rows": rows, "gaps": ["对标高表现内容的互动数据更好，我方需要进一步明确用户需求和内容收益。", "检查我方正文是否包含具体场景、证据、步骤或可执行建议。", "学习对标内容的选题切入和结构，但替换为自己的案例、素材和表达。"]}


def adjust_strategy(posts: list[dict[str, Any]], feedback: list[dict[str, Any]]) -> list[str]:
    if not feedback:
        return ["尚无后续表现数据。发布计划后补充反馈 CSV，Agent 会根据互动结果调整策略。"]
    for row in feedback:
        row["engagement"] = number(row.get("likes", 0)) + number(row.get("collects", 0)) + number(row.get("comments", 0))
    average = sum(row["engagement"] for row in feedback) / len(feedback)
    best = max(feedback, key=lambda row: row["engagement"])
    return [f"已分析 {len(feedback)} 条我方发布反馈，平均互动为 {average:.0f}。", f"表现最好的是“{best.get('title', '未命名')}”（互动 {best['engagement']}），下一轮优先保留它的选题角度和内容结构。", "对低于平均互动的内容，优先调整标题前两句、封面信息密度和结尾互动问题。", "每新增一轮反馈，重新比较高表现主题、内容类型和 CTA，逐步减少低表现方向。"]


def init_review_db(db_path: Path = DB_PATH) -> None:
    with sqlite3.connect(db_path) as conn:
        conn.execute("CREATE TABLE IF NOT EXISTS reviews (id INTEGER PRIMARY KEY AUTOINCREMENT, plan_id TEXT, title TEXT, angle TEXT, decision TEXT, reason TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP)")


def save_review(plan: dict[str, Any], decision: str, reason: str, db_path: Path = DB_PATH) -> None:
    init_review_db(db_path)
    with sqlite3.connect(db_path) as conn:
        conn.execute("INSERT INTO reviews(plan_id,title,angle,decision,reason) VALUES (?,?,?,?,?)", (plan["plan_id"], plan["title"], plan["angle"], decision, reason.strip()))


def review_summary(db_path: Path = DB_PATH) -> dict[str, Any]:
    init_review_db(db_path)
    with sqlite3.connect(db_path) as conn:
        rows = conn.execute("SELECT plan_id,title,angle,decision,reason,created_at FROM reviews ORDER BY id DESC").fetchall()
    accepted = [row for row in rows if row[3] == "采纳"]
    rejected = [row for row in rows if row[3] == "驳回"]
    return {"rows": rows, "accepted": accepted, "rejected": rejected, "accepted_angles": sorted({row[2] for row in accepted})}


def content_templates() -> list[dict[str, str]]:
    return [
        {"模板名称": "问题解决型", "适用场景": "用户有明确困扰", "结构": "痛点标题 -> 真实场景 -> 3个方法 -> 适用边界 -> 提问", "注意": "方法和案例必须原创"},
        {"模板名称": "场景实测型", "适用场景": "展示亲身测试或过程", "结构": "测试目标 -> 操作过程 -> 前后变化 -> 结果证据 -> 复盘", "注意": "不能虚构测试结果"},
        {"模板名称": "清单对比型", "适用场景": "书单、工具或方案比较", "结构": "选择标准 -> 3-5个选项 -> 优缺点 -> 推荐人群 -> 收藏提示", "注意": "避免复制对标账号排序"},
        {"模板名称": "误区纠正型", "适用场景": "纠正常见认知", "结构": "常见误区 -> 为什么不对 -> 正确做法 -> 例子 -> 互动讨论", "注意": "事实和引用需要核验"},
    ]


def api_analyze4(posts: list[dict[str, Any]], result: dict[str, Any], api_key: str,
                 base_url: str, model: str, timeout_seconds: int = 60,
                 wire_api: str = "responses", reasoning_effort: str = "medium",
                 lightweight: bool = False) -> str:
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise RuntimeError("未安装 openai，请执行 pip install openai") from exc
    if not api_key.strip():
        raise ValueError("API Key 不能为空")
    client = OpenAI(api_key=api_key.strip(), base_url=base_url.strip() or None,
                    timeout=timeout_seconds, max_retries=0)
    selected_posts = posts
    if lightweight:
        selected_posts = sorted(posts, key=lambda item: item["engagement"], reverse=True)[:3]
        selected_posts = [{
            "account_name": p["account_name"], "account_positioning": p["account_positioning"],
            "title": p["title"], "content": p["content"][:220], "hashtags": p["hashtags"],
            "content_type": p.get("content_type", ""), "likes": p["likes"],
            "collects": p["collects"], "comments": p["comments"], "engagement": p["engagement"],
        } for p in selected_posts]
    prompt = (
        "你是对标账号研究与内容策略分析师。请基于输入的公开笔记数据完成第4题分析。\n"
        "重点输出：1. 高表现内容的真实选题及用户需求；2. 可借鉴的内容机制与不能照搬的具体表达；"
        "3. 为我方账号生成差异化内容计划；4. 检查相似和抄袭风险；5. 给出后续学习策略。\n"
        "不得复制原文、书摘、案例和图片描述，不确定的信息标记需要人工确认。请输出结构清晰的中文 Markdown。\n\n" +
        ("这是轻量模式，只分析互动最高的 3 篇笔记摘要。请优先快速返回结果。\n" if lightweight else "") +
        "分析摘要：\n" + json.dumps({
            "profiles": result["profiles"], "topic_summary": result["topic_summary"],
            "mechanisms": result["mechanisms"], "opportunities": result["opportunities"],
            "plans": result["plans"], "similarity": result["similarity"],
        }, ensure_ascii=False) + "\n\n输入笔记摘要：\n" + json.dumps(selected_posts, ensure_ascii=False)
    )
    selected_model = model.strip() or "gpt-4o-mini"
    if wire_api == "responses":
        response = client.responses.create(
            model=selected_model,
            input=prompt,
            reasoning={"effort": reasoning_effort},
        )
    else:
        response = client.chat.completions.create(
            model=selected_model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
        )
    if isinstance(response, str):
        return response.strip()
    if isinstance(response, dict):
        if response.get("output_text"):
            return str(response["output_text"]).strip()
        choices = response.get("choices") or []
        content = (choices[0].get("message", {}).get("content") if choices else None) or response.get("output_text", "")
        return str(content).strip()
    choices = getattr(response, "choices", None) or []
    if choices:
        return str(getattr(getattr(choices[0], "message", None), "content", "") or "").strip()
    return str(getattr(response, "output_text", "") or "").strip()


def api_analyze4_stream(posts: list[dict[str, Any]], result: dict[str, Any], api_key: str,
                        base_url: str, model: str, timeout_seconds: int = 60,
                        wire_api: str = "responses", reasoning_effort: str = "medium",
                        lightweight: bool = True):
    """Yield text deltas from an OpenAI-compatible streaming request."""
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise RuntimeError("未安装 openai，请执行 pip install openai") from exc
    if not api_key.strip():
        raise ValueError("API Key 不能为空")
    client = OpenAI(api_key=api_key.strip(), base_url=base_url.strip() or None,
                    timeout=timeout_seconds, max_retries=0)
    selected_posts = sorted(posts, key=lambda item: item["engagement"], reverse=True)[:3] if lightweight else posts
    post_data = [{"account_name": p["account_name"], "title": p["title"], "content": p["content"][:220] if lightweight else p["content"], "hashtags": p["hashtags"], "likes": p["likes"], "collects": p["collects"], "comments": p["comments"], "engagement": p["engagement"]} for p in selected_posts]
    prompt = (
        "你是对标账号研究与内容策略分析师。请基于公开笔记完成第4题分析。\n"
        "输出：高表现选题、可借鉴机制与不能照搬表达、我方差异化计划、标题和内容关键词相似度风险、后续策略。\n"
        "不得复制原文、书摘、案例和图片描述；不确定内容标记需要人工确认。输出中文 Markdown。\n"
        + ("这是轻量模式，只分析互动最高的3篇笔记摘要。\n" if lightweight else "")
        + json.dumps({"profiles": result["profiles"], "topic_summary": result["topic_summary"], "mechanisms": result["mechanisms"], "opportunities": result["opportunities"], "plans": result["plans"], "similarity": result["similarity"], "posts": post_data}, ensure_ascii=False)
    )
    selected_model = model.strip() or "gpt-4o-mini"
    if wire_api == "responses":
        with client.responses.stream(model=selected_model, input=prompt, reasoning={"effort": reasoning_effort}) as stream:
            for event in stream:
                if getattr(event, "type", "") == "response.output_text.delta":
                    delta = getattr(event, "delta", "")
                    if delta:
                        yield delta
    else:
        stream = client.chat.completions.create(model=selected_model, messages=[{"role": "user", "content": prompt}], temperature=0.7, stream=True)
        for chunk in stream:
            choices = getattr(chunk, "choices", None) or []
            if choices:
                delta = getattr(getattr(choices[0], "delta", None), "content", "") or ""
                if delta:
                    yield delta
