# 小红书竞品账号分析与差异化内容 Agent

这是一个基于人工整理公开笔记数据的小红书内容研究工具。它不爬取小红书，也不需要账号登录，而是通过 CSV 文件分析竞品账号的定位、选题、内容结构和互动表现，并为你的账号生成可执行的原创内容方向。

## 主要功能

- 按账号生成账号画像，比较内容类型和平均互动表现；
- 提炼高表现笔记的选题、标题 Hook、内容结构和标签使用方式；
- 区分可以借鉴的方法与不能直接复制的文字、案例和素材；
- 根据你的账号定位生成差异化标题、内容结构、关键词和互动 CTA；
- 使用文本相似度初步检查生成内容的相似或抄袭风险；
- 对比我方内容与竞品高表现内容的差距；
- 上传后续发布反馈，辅助调整下一轮内容策略；
- 支持人工审核内容计划，并将审核记录保存到本地 SQLite 数据库；
- 可选调用 OpenAI 兼容 API，生成更深入的中文分析报告。

## 运行方式

安装依赖：

```bash
pip install -r requirements.txt
```

启动 Streamlit 页面：

```bash
streamlit run xiaohongshu4_app.py
```

应用默认读取同目录下的 `xiaohongshu4_posts.csv`，也可以在页面上传其他符合格式的 CSV 文件。

页面中的 API 分析支持 Responses API 和 Chat Completions 两种协议。结果会边生成边显示（可关闭流式输出），生成后可以直接编辑，并在“栏目化视图”和“原始 Markdown”之间切换；流式接口不兼容时会自动尝试同步请求。

## CSV 必填字段

```text
account_id,account_name,account_positioning,post_id,title,content,hashtags,publish_time,likes,collects,comments,is_viral
```

## 可选字段

```text
author,url,image_path,cover_description,target_audience,content_type,notes
```

其中 `is_viral` 支持 `TRUE` 或 `FALSE`。互动数据会被转换为数值，并按点赞、收藏和评论之和计算综合互动量。

## 项目文件

- `xiaohongshu4_app.py`：Streamlit 网页应用入口；
- `xiaohongshu4_core.py`：CSV 读取、账号分析、内容计划生成、相似度检查和审核记录等核心逻辑；
- `xiaohongshu4_posts.csv`：示例竞品笔记数据；
- `requirements.txt`：Python 依赖列表。

## 使用边界

分析结果用于内容研究和创作辅助，不等同于法律意义上的抄袭判定。发布内容时应使用原创案例、图片和表达，并人工核验书名、数据、品牌及引用来源。
