import streamlit as st
from pathlib import Path
from xiaohongshu4_core import adjust_strategy, analyze, api_analyze4, api_analyze4_stream, compare_own_content, content_templates, read_csv, read_feedback, review_summary, save_review

st.set_page_config(page_title="对标账号学习 Agent", page_icon="📊", layout="wide")
st.title("小红书对标账号学习与差异化内容 Agent")
st.caption("人工整理公开笔记 -> 账号画像 -> 提炼机制 -> 生成原创内容计划")

with st.sidebar:
    upload = st.file_uploader("上传第 4 题 CSV", type=["csv"])
    feedback_upload = st.file_uploader("上传我方后续表现反馈 CSV（可选）", type=["csv"])
    own_positioning = st.text_input("你的账号定位", placeholder="例如：给职场新人的读书方法")
    st.info("本模块不爬虫、不登录小红书，只分析你上传或人工整理的数据。")
    if "api4" not in st.session_state:
        st.session_state["api4"] = {"key": "", "base_url": "https://api.openai.com/v1", "model": "gpt-4o-mini", "timeout": 60, "wire_api": "responses", "reasoning_effort": "medium"}

    @st.dialog("第 4 题 API 设置")
    def api_dialog():
        current = st.session_state["api4"]
        key = st.text_input("API Key", value=current["key"], type="password")
        base_url = st.text_input("Base URL", value=current["base_url"], help="填写 API 地址，不要填网站首页")
        model = st.text_input("模型名称", value=current["model"])
        timeout = st.number_input("超时秒数", min_value=15, max_value=600, value=current["timeout"])
        wire_api = st.selectbox("Wire API", ["responses", "chat_completions"], index=0 if current.get("wire_api", "responses") == "responses" else 1, help="OpenAI Responses API 或 Chat Completions API")
        reasoning_effort = st.selectbox("推理强度", ["low", "medium", "high"], index=["low", "medium", "high"].index(current.get("reasoning_effort", "medium")), help="仅 Responses API 生效")
        if st.button("保存设置", type="primary"):
            st.session_state["api4"] = {"key": key, "base_url": base_url, "model": model, "timeout": timeout, "wire_api": wire_api, "reasoning_effort": reasoning_effort}
            st.success("API 设置已保存")
            st.rerun()
    if st.button("设置 API"):
        api_dialog()
    st.caption("API：已配置" if st.session_state["api4"]["key"] else "API：未配置")

# The bundled dataset is the user's real benchmark-account export.
source = upload or Path(__file__).with_name("小红书不同账号对标.csv")
try:
    posts = read_csv(source)
except Exception as error:
    st.error(f"读取失败：{error}")
    st.stop()

st.success(f"已读取 {len(posts)} 篇笔记，涉及 {len({p['account_id'] for p in posts})} 个账号")
with st.expander("查看原始数据"):
    st.dataframe(posts, use_container_width=True, hide_index=True)
if st.button("开始分析", type="primary", use_container_width=True):
    st.session_state["result"] = analyze(posts, own_positioning)
result = st.session_state.get("result")
if not result:
    st.stop()

api_mode = st.checkbox("使用 API 深度分析", value=False)
api_lightweight = st.radio("API 请求模式", ["轻量模式（推荐，发送高表现笔记摘要）", "完整模式（发送全部数据）"], horizontal=True)
api_streaming = st.checkbox("使用流式输出（边生成边显示）", value=True, help="Responses API 和 Chat Completions API 均支持；结束后会保存完整结果")
if api_mode and st.button("调用 API 分析", use_container_width=True):
    settings = st.session_state["api4"]
    try:
        with st.spinner("正在调用 API 分析对标选题和差异化策略..."):
            if api_streaming:
                placeholder = st.empty()
                collected = ""
                for delta in api_analyze4_stream(posts, result, settings["key"], settings["base_url"], settings["model"], settings["timeout"], settings.get("wire_api", "responses"), settings.get("reasoning_effort", "medium"), api_lightweight.startswith("轻量")):
                    collected += delta
                    placeholder.markdown(collected)
                st.session_state["api4_result"] = collected
            else:
                st.session_state["api4_result"] = api_analyze4(posts, result, settings["key"], settings["base_url"], settings["model"], settings["timeout"], settings.get("wire_api", "responses"), settings.get("reasoning_effort", "medium"), api_lightweight.startswith("轻量"))
    except Exception as error:
        st.error(f"API 调用失败：{error}")
        st.session_state["api4_result"] = None
if st.session_state.get("api4_result"):
    st.subheader("API 深度分析结果")
    api_text = st.session_state["api4_result"]
    st.success(f"API 返回成功，共 {len(api_text)} 个字符")
    st.markdown(api_text)
    with st.expander("查看 API 原始文本"):
        st.code(api_text, language="markdown")
    st.download_button("导出 API 分析", api_text, "xiaohongshu4_api_analysis.md", "text/markdown")
elif api_mode:
    st.info("尚未获得 API 结果。请确认已配置 API，并点击“调用 API 分析”。")

st.subheader("1. 对标账号画像")
st.dataframe(result["profiles"], use_container_width=True, hide_index=True)
st.write("高表现内容常见标签：", result["common_tags"] or "未识别到标签")

st.subheader("2. 高表现内容选题总结")
st.caption("这里分析的是内容在讨论什么、服务什么需求，以及选题机制如何迁移；不是只分析标题写法。")
st.dataframe(result["topic_summary"], use_container_width=True, hide_index=True)

left, right = st.columns(2)
with left:
    st.subheader("3. 共同有效机制")
    st.caption("可借鉴的是内容方法和结构；不能照搬的是原账号的具体文字、案例、素材和标签组合。")
    st.dataframe(result["mechanisms"], use_container_width=True, hide_index=True)
    st.subheader("4. 不可直接照搬")
    for item in result["risks"]: st.write("- " + item)
with right:
    st.subheader("5. 你的差异化机会")
    for item in result["opportunities"]: st.write("- " + item)

st.subheader("6. 原创差异化内容计划")
st.dataframe(result["plans"], use_container_width=True, hide_index=True)
st.download_button("导出内容计划 CSV", "\ufeff" + "\n".join(",".join(str(item[field]).replace(",", "，") for field in item) for item in result["plans"]), "xiaohongshu4_content_plan.csv", "text/csv")

st.subheader("7. 可复用内容模板")
st.dataframe(content_templates(), use_container_width=True, hide_index=True)

st.subheader("8. 人工审核")
st.caption("请逐条选择采纳或驳回，并填写理由。审核记录会保存到本地 reviews.db，后续用于总结规律和风险提醒。")
for plan in result["plans"]:
    with st.container(border=True):
        st.markdown(f"**{plan['plan_id']}｜{plan['title']}**")
        st.write(f"角度：{plan['angle']} ｜ Hook：{plan['hook']}")
        st.write(f"结构：{plan['structure']}")
        decision = st.radio("审核结果", ["待审核", "采纳", "驳回"], key=f"decision_{plan['plan_id']}", horizontal=True)
        reason = st.text_area("审核理由", key=f"reason_{plan['plan_id']}", placeholder="例如：采纳，因为符合账号定位；或驳回，因为标题太像对标账号。")
        if st.button("保存审核", key=f"save_review_{plan['plan_id']}"):
            if decision == "待审核":
                st.warning("请先选择采纳或驳回。")
            elif not reason.strip():
                st.warning("请填写审核理由。")
            else:
                save_review(plan, decision, reason)
                st.success("审核记录已保存。")

st.subheader("9. 审核规律沉淀")
summary = review_summary()
st.write(f"累计审核：{len(summary['rows'])} 条；采纳：{len(summary['accepted'])} 条；驳回：{len(summary['rejected'])} 条。")
if summary["accepted_angles"]:
    st.write("已采纳角度：" + "、".join(summary["accepted_angles"]))
if summary["rejected"]:
    st.warning("历史驳回理由（生成新内容时请重点检查）：")
    for row in summary["rejected"][:10]:
        st.write(f"- {row[1]}：{row[4]}")
with st.expander("查看全部审核记录"):
    st.dataframe([{"计划": r[0], "标题": r[1], "角度": r[2], "结果": r[3], "理由": r[4], "时间": r[5]} for r in summary["rows"]], use_container_width=True, hide_index=True)

st.subheader("10. 我方内容与对标账号对比")
st.caption("填写自己的内容，比较标题、正文、标签的差距和相似风险。")
with st.form("own_content_form"):
    own_title = st.text_input("我方标题")
    own_content = st.text_area("我方正文", height=160)
    own_tags = st.text_input("我方标签")
    compare_clicked = st.form_submit_button("分析我方与对标内容")
if compare_clicked:
    if not own_title.strip() or not own_content.strip():
        st.warning("我方标题和正文不能为空。")
    else:
        st.session_state["own_compare"] = compare_own_content({"title": own_title, "content": own_content, "hashtags": own_tags}, posts)
own_compare = st.session_state.get("own_compare")
if own_compare:
    st.write(f"当前对比的高表现样本：{own_compare['benchmark']['title']}")
    st.dataframe(own_compare["rows"], use_container_width=True, hide_index=True)
    st.write("差距与学习建议：")
    for gap in own_compare["gaps"]: st.write("- " + gap)

st.subheader("11. 生成内容相似度与抄袭风险")
st.dataframe(result["similarity"], use_container_width=True, hide_index=True)
st.caption("第 11 点同时检查生成标题、内容关键词、对标内容关键词/片段和结构；相似度只是初筛指标，不等同于法律意义上的抄袭结论。")

st.subheader("12. 根据后续表现调整学习策略")
feedback = []
if feedback_upload:
    try:
        feedback = read_feedback(feedback_upload)
    except Exception as error:
        st.warning(f"反馈 CSV 读取失败：{error}")
st.info("反馈 CSV 至少包含 title、likes、collects、comments 字段；也可以沿用当前 CSV 字段格式。")
for advice in adjust_strategy(posts, feedback):
    st.write("- " + advice)
