# 第 4 题：对标账号学习与差异化内容 Agent

本目录独立于第 5 题代码。第 4 题使用人工整理的公开小红书笔记，不需要爬虫或账号登录。

当前 Agent 默认使用目录中的 `小红书不同账号对标.csv`。也可以在页面上传其他同结构 CSV。Agent 会按账号分组，分析账号定位、选题、Hook、结构、互动方式和发布节奏，并生成差异化原创内容计划。

## CSV 必填字段

```text
account_id,account_name,account_positioning,post_id,title,content,hashtags,publish_time,likes,collects,comments,is_viral
```

## 可选字段

```text
author,url,image_path,cover_description,target_audience,content_type,notes
```

`is_viral` 使用 `TRUE` 或 `FALSE`。图片可以先填写本地图片路径；如果只做文字 Demo，可以留空。账号定位和目标用户建议每篇同账号笔记保持一致。

当前数据已包含 4 个账号、12 篇笔记，页面会直接基于这些数据运行第 4 题 Demo。
