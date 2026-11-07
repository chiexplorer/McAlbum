## 项目概述

McAlbum 是一个用于记录和展示 Minecraft Fabric 纯净生存服务器的“世界档案馆”。核心内容包括服务器简介、照片与玩家评论、主题历史作品集和玩家志。

项目首先服务内容浏览和长期保存，不建设成通用服务器面板。设计与实现细节以以下文档为准：

- `docs/需求描述.md`：产品定位、内容结构与视觉方向；
- `docs/功能模块设计.md`：模块行为、体验边界与验收要求；
- `docs/技术路线.md`：技术选型、数据、数据库和媒体方案。
- `docs/实施计划.md`：阶段顺序、媒体导入、纵向切片与发布条件。

## 技术栈

### 前端

- Nuxt 4、Vue 3、TypeScript；
- Node.js 最低版本为 22.22.3，以根目录 `.nvmrc` 为准；
- Zod 校验结构化内容；
- Nuxt Image 负责响应式图片能力；
- 原生 CSS/CSS Variables 或 Sass；
- Vitest 与 Playwright；
- 第一阶段采用静态生成，只有筛选、图片查看器、导航等必要功能使用客户端 JavaScript。

### 内容

- 所有结构化内容使用 JSON，不使用 YAML；
- JSON 内容位于根目录 `content/`；
- JSON Schema 位于 `contracts/json-schema/`，是静态内容格式的权威契约；
- Zod 是前端运行时镜像；字段变更必须同步更新 JSON Schema、Zod 和契约测试；
- 实体使用稳定的小写 kebab-case ID，显示名称变化时不得修改 ID；
- 项目时区固定为中国北京，数据和程序使用 `Asia/Shanghai`；
- 页面与组件通过 repository/service 访问内容，不直接散落导入 JSON 文件；
- 照片、玩家和作品集通过 ID 建立关系；项目只记录一个持续运行的服务器世界，不建模周目、地点或事件实体。
- 首页固定作品集使用 `content/built-in-stories/` 中的内置包，其 WebP 变体位于 `apps/web/public/built-in-stories/` 并随 Git 发布；内置作品集为只读内容，不由数据库、上传流程或媒体清理命令管理。

### 后端与数据库

- FastAPI、Pydantic、SQLAlchemy 2、Alembic；
- 生产数据库确定为 MySQL，所有业务表使用 InnoDB 与 `utf8mb4`；
- 开发、集成测试和生产使用相同数据库类型，SQLite 不替代 MySQL 集成测试；
- 第一阶段可以不部署 FastAPI，但必须维护 `apps/api` 的边界，不把未来后端职责塞入前端；
- 玩家登录、投稿、评论或权限管理一旦启用，FastAPI 与 MySQL 即成为必需依赖，不能用纯前端逻辑代替；
- FastAPI 启用后使用 Router → Service → Repository → SQLAlchemy/File Storage 分层；
- 数据库迁移通过 Alembic 管理，禁止在生产应用启动时自动建表。

### 账号与权限

- 身份分为未登录访客、普通用户和管理员；访客不是数据库角色；
- 权限采用固定角色、固定能力标识和内容归属校验；管理员可调整固定角色的权限映射，但不实现通用 ACL、逐用户权限覆盖或任意角色编辑器；
- 用户自行提交注册申请，账号预分配普通用户角色并保持 `pending`；管理员批准后变为 `active`，拒绝后变为 `rejected`；不使用邀请码；
- 注册时同一 IP 和同一账号标识在配置窗口内分别最多提交 5 次；密码至少 8 位且同时包含字母和数字；
- 封禁使用账号 `banned` 状态而不是角色，并撤销现有会话；
- 用户账号与玩家档案分离，停用账号不得级联删除玩家档案或历史内容；
- 普通用户默认只能编辑自己的玩家资料和本人内容，模块投稿与直接发布权限分开授予；
- 认证使用服务端会话与 `HttpOnly`、`Secure`、`SameSite` Cookie，密码使用 Argon2id 哈希；
- 不把长期 JWT 保存到 `localStorage`；
- 权限、内容归属、状态转换和公开字段过滤必须由 FastAPI 校验，不能只依靠前端隐藏按钮；
- 照片和作品集日常使用 `draft`、`published`、`archived`、`deleted` 状态，并兼容既有 `pending`、`rejected` 数据；
- 权限变更、发布或下架、评论隐藏或恢复必须留下必要审计记录。

### 图片存储

- 图片文件存放于本地持久化文件系统，数据库只保存元数据和业务关系；
- `storage/originals` 保存原图，`storage/variants` 保存公开变体；
- `storage/temporary` 和 `storage/quarantine` 不对外公开；
- 数据库只保存相对于媒体根目录的路径，不保存绝对路径；
- 公开图片应由 Nginx 等静态服务器提供，FastAPI 负责上传、校验、处理和元数据；
- 文件写入与数据库记录通过 `pending`、`ready`、`failed`、`deleted` 状态处理非原子一致性；
- 原图必须备份，变体应可重建。

## 项目结构

```text
apps/
├── web/                    # Nuxt 前端
│   └── app/
│       ├── components/     # 基础组件和业务组件
│       ├── pages/          # 路由页面
│       ├── repositories/   # 内容访问接口及实现
│       ├── schemas/        # Zod 领域模型
│       └── services/       # 跨实体前端业务逻辑
└── api/                    # FastAPI 后端
    ├── app/
    │   ├── api/            # HTTP 路由
    │   ├── core/           # 配置和基础设施
    │   ├── models/         # SQLAlchemy 模型
    │   ├── repositories/   # 数据库和文件访问
    │   ├── schemas/        # Pydantic 输入输出模型
    │   └── services/       # 业务规则
    ├── migrations/         # Alembic 迁移
    └── tests/
content/                    # 第一阶段 JSON 内容源
├── built-in-stories/       # 随代码发布的只读内置作品集
contracts/
├── json-schema/            # JSON 内容契约
└── openapi/                # FastAPI OpenAPI 快照
storage/                    # 不提交实际文件的本地媒体目录
deploy/                     # Nginx 等生产部署示例
scripts/                    # 内容导入、校验和图片处理工具
docs/                       # 产品、功能和技术文档
```

新增代码时优先放入职责最明确的现有目录。只有出现新的稳定职责时才增加顶层目录。

## 架构约定

- 公开页面保留静态生成的首屏与故障兜底；照片和作品集等已发布内容通过公开只读 API 在浏览器刷新时同步，静态重建用于 SEO 和归档，不是日常发布前置条件；
- 页面不能直接依赖具体数据源，应依赖 `ContentRepository` 等抽象，以便从 JSON 平滑切换到 API；
- 核心关系字段使用普通数据库列、主键、外键和关联表，不把所有数据塞进 MySQL JSON 列；
- JSON 列只用于作品集内容区块、展示配置等低频关联的灵活数据；
- 筛选状态写入 URL，详情内容必须拥有可分享的稳定 URL；
- 第一阶段不引入 Pinia、大型 UI 库、地图引擎、动画框架或实时服务，除非需求已证明必要；
- 静态首版的玩家语录作为内容维护；协作阶段只开放已登录用户的异步评论，不开放匿名或实时聊天式评论；
- 图片必须声明尺寸和替代文本，首屏外图片默认懒加载；
- 所有关键交互必须支持键盘操作和 `prefers-reduced-motion`。

## 常用命令

在仓库根目录运行：

```powershell
npm install
npm run dev:web
npm run typecheck:web
npm run test:web
npm run generate:web
npm run validate:content
npm run validate:content:release
npm run import:media
npm run sync:public-content
```

在 `apps/api` 安装开发依赖后运行：

```powershell
python -m pytest
python -m ruff check .
python -m uvicorn app.main:app --reload
```

任何涉及内容结构的变更至少运行内容校验；前端变更至少运行类型检查和相关测试；后端变更至少运行 Ruff 和 pytest。

## 重要约定

- 修改代码前，如果有我没提及但你认为有必要提及的事项，可以先找我确认。
- 如果可以，按层层递进的风格组织代码，即先聚合整体，再展开各部分。
- 关于注释：
  - 使用中文；
  - 对于函数和对象，视逻辑复杂程度选择如下注释粒度：
    - 简单：单行注释描述其功能；
    - 中等：描述功能，并给出输入参数含义；
    - 复杂：描述功能、设计模式（若有）、输出参数、输出含义，并给出调用示例。
- 当需要分析代码时，请同样遵循层层递进的叙述风格，即先描述整体，再展开细节。
- 依赖版本变更必须同步更新锁文件并运行相关验证。
- 新增环境变量时同步更新 `.env.example`，不得提交真实密码、令牌或服务器地址。
- 业务时间在数据库中保存为 UTC，显示时再转换到目标时区。
- 内容 ID、路由 slug 和媒体 storage key 一经发布不得随意修改。
- `apps/web/app/generated/media-assets.json` 是自动生成的浏览器安全媒体投影，不得手工修改；前端不得直接导入包含原图路径和哈希的完整媒体清单。
- `apps/web/app/generated/content.json` 是自动生成的脱敏内容投影；前端不得绕过它直接打包玩家或评论源 JSON。
- 合并前端或内容变更前运行 `npm run check:web`；正式发布前必须设置正式 `NUXT_PUBLIC_SITE_URL` 并运行 `npm run check:release`。
- 发布时归档 `apps/web/.output/release-manifest.json` 和原图备份，以便核验和恢复同一快照。
- Nuxt 开发与预览服务不得暴露到公网；生产环境部署静态生成产物，并由 Nginx 代理 FastAPI、映射 `storage/variants` 和为动态详情路由回退到 `200.html`。
- 当前 Nuxt 构建链存在尚无上游修复版本的 `node-forge` 间接依赖公告；升级依赖时必须重新运行 `npm audit` 并优先采用修复版本。

## 禁止事项

- 代码没有改动的部分，不要删我写的注释。
- 不直接把用户上传文件名作为磁盘文件名。
- 不在数据库中保存图片二进制 BLOB。
- 不在 Git 中提交真实媒体文件、数据库文件、`.env` 或构建产物。
- 不绕过 repository/service 层让页面直接访问数据库或任意读取文件系统。
- 不使用 SQLite 冒充 MySQL 完成集成测试。
- 不为权限需求引入通用策略引擎、Redis、对象存储、消息队列或分布式任务系统。

<skills_system priority="1">

# AGENTS

<skills_system priority="1">

## Available Skills

<!-- SKILLS_TABLE_START -->
<usage>
When users ask you to perform tasks, check if any of the available skills below can help complete the task more effectively. Skills provide specialized capabilities and domain knowledge.

How to use skills:
- Invoke: `npx openskills read <skill-name>` (run in your shell)
  - For multiple: `npx openskills read skill-one,skill-two`
- The skill content will load with detailed instructions on how to complete the task
- Base directory provided in output for resolving bundled resources (references/, scripts/, assets/)

Usage notes:
- Only use skills listed in <available_skills> below
- Do not invoke a skill that is already loaded in your context
- Each skill invocation is stateless
</usage>

<available_skills>

<skill>
<name>academy-guide</name>
<description>></description>
<location>project</location>
</skill>

<skill>
<name>algorithmic-art</name>
<description>Creating algorithmic art using p5.js with seeded randomness and interactive parameter exploration. Use this when users request creating art using code, generative art, algorithmic art, flow fields, or particle systems. Create original algorithmic art rather than copying existing artists' work to avoid copyright violations.</description>
<location>project</location>
</skill>

<skill>
<name>brand-guidelines</name>
<description>Applies Anthropic's official brand colors and typography to any sort of artifact that may benefit from having Anthropic's look-and-feel. Use it when brand colors or style guidelines, visual formatting, or company design standards apply.</description>
<location>project</location>
</skill>

<skill>
<name>canvas-design</name>
<description>Create beautiful visual art in .png and .pdf documents using design philosophy. You should use this skill when the user asks to create a poster, piece of art, design, or other static piece. Create original visual designs, never copying existing artists' work to avoid copyright violations.</description>
<location>project</location>
</skill>

<skill>
<name>claude-api</name>
<description>|-</description>
<location>project</location>
</skill>

<skill>
<name>discernment-nudge</name>
<description>></description>
<location>project</location>
</skill>

<skill>
<name>doc-coauthoring</name>
<description>Guide users through a structured workflow for co-authoring documentation. Use when user wants to write documentation, proposals, technical specs, decision docs, or similar structured content. This workflow helps users efficiently transfer context, refine content through iteration, and verify the doc works for readers. Trigger when user mentions writing docs, creating proposals, drafting specs, or similar documentation tasks.</description>
<location>project</location>
</skill>

<skill>
<name>docx</name>
<description>"Use this skill whenever the user wants to create, read, edit, or manipulate Word documents (.docx files) or Word templates (.dotx files). Triggers include: any mention of 'Word doc', 'word document', '.docx', '.dotx', or requests to produce professional documents with formatting like tables of contents, headings, page numbers, or letterheads. Also use when extracting or reorganizing content from .docx or .dotx files, inserting or replacing images in documents, performing find-and-replace in Word files, working with tracked changes or comments, or converting content into a polished Word document. If the user asks for a 'report', 'memo', 'letter', 'template', or similar deliverable as a Word or .docx file, use this skill. Do NOT use for PDFs, spreadsheets, Google Docs, or general coding tasks unrelated to document generation."</description>
<location>project</location>
</skill>

<skill>
<name>frontend-design</name>
<description>Guidance for distinctive, intentional visual design when building new UI or reshaping an existing one. Helps with aesthetic direction, typography, and making choices that don't read as templated defaults.</description>
<location>project</location>
</skill>

<skill>
<name>internal-comms</name>
<description>A set of resources to help me write all kinds of internal communications, using the formats that my company likes to use. Claude should use this skill whenever asked to write some sort of internal communications (status reports, leadership updates, 3P updates, company newsletters, FAQs, incident reports, project updates, etc.).</description>
<location>project</location>
</skill>

<skill>
<name>mcp-builder</name>
<description>Guide for creating high-quality MCP (Model Context Protocol) servers that enable LLMs to interact with external services through well-designed tools. Use when building MCP servers to integrate external APIs or services, whether in Python (FastMCP) or Node/TypeScript (MCP SDK).</description>
<location>project</location>
</skill>

<skill>
<name>pdf</name>
<description>Use this skill whenever the user wants to do anything with PDF files. This includes reading or extracting text/tables from PDFs, combining or merging multiple PDFs into one, splitting PDFs apart, rotating pages, adding watermarks, creating new PDFs, filling PDF forms, encrypting/decrypting PDFs, extracting images, and OCR on scanned PDFs to make them searchable. If the user mentions a .pdf file or asks to produce one, use this skill.</description>
<location>project</location>
</skill>

<skill>
<name>pptx</name>
<description>"Use this skill any time a .pptx or .potx file is involved in any way — as input, output, or both. This includes: creating slide decks, pitch decks, or presentations; reading, parsing, or extracting text from any .pptx or .potx file (even if the extracted content will be used elsewhere, like in an email or summary); editing, modifying, or updating existing presentations; combining or splitting slide files; working with templates (.potx), layouts, speaker notes, or comments. Trigger whenever the user mentions \"deck,\" \"slides,\" \"presentation,\" or references a .pptx or .potx filename, regardless of what they plan to do with the content afterward. If a .pptx or .potx file needs to be opened, created, or touched, use this skill."</description>
<location>project</location>
</skill>

<skill>
<name>skill-creator</name>
<description>Create new skills, modify and improve existing skills, and measure skill performance. Use when users want to create a skill from scratch, edit, or optimize an existing skill, run evals to test a skill, benchmark skill performance with variance analysis, or optimize a skill's description for better triggering accuracy.</description>
<location>project</location>
</skill>

<skill>
<name>slack-gif-creator</name>
<description>Knowledge and utilities for creating animated GIFs optimized for Slack. Provides constraints, validation tools, and animation concepts. Use when users request animated GIFs for Slack like "make me a GIF of X doing Y for Slack."</description>
<location>project</location>
</skill>

<skill>
<name>template</name>
<description>Replace with description of the skill and when Claude should use it.</description>
<location>project</location>
</skill>

<skill>
<name>theme-factory</name>
<description>Toolkit for styling artifacts with a theme. These artifacts can be slides, docs, reportings, HTML landing pages, etc. There are 10 pre-set themes with colors/fonts that you can apply to any artifact that has been creating, or can generate a new theme on-the-fly.</description>
<location>project</location>
</skill>

<skill>
<name>web-artifacts-builder</name>
<description>Suite of tools for creating elaborate, multi-component claude.ai HTML artifacts using modern frontend web technologies (React, Tailwind CSS, shadcn/ui). Use for complex artifacts requiring state management, routing, or shadcn/ui components - not for simple single-file HTML/JSX artifacts.</description>
<location>project</location>
</skill>

<skill>
<name>webapp-testing</name>
<description>Toolkit for interacting with and testing local web applications using Playwright. Supports verifying frontend functionality, debugging UI behavior, capturing browser screenshots, and viewing browser logs.</description>
<location>project</location>
</skill>

<skill>
<name>xlsx</name>
<description>"Use this skill any time a spreadsheet file is the primary input or output. This means any task where the user wants to: open, read, edit, or fix an existing .xlsx, .xlsm, .xltx, .csv, or .tsv file (e.g., adding columns, computing formulas, formatting, charting, cleaning messy data); create a new spreadsheet from scratch or from other data sources; or convert between tabular file formats. Trigger especially when the user references a spreadsheet file by name or path — even casually (like \"the xlsx in my downloads\") — and wants something done to it or produced from it. Also trigger for cleaning or restructuring messy tabular data files (malformed rows, misplaced headers, junk data) into proper spreadsheets. The deliverable must be a spreadsheet file. Do NOT trigger when the primary deliverable is a Word document, HTML report, standalone Python script, database pipeline, or Google Sheets API integration, even if tabular data is involved."</description>
<location>project</location>
</skill>

</available_skills>
<!-- SKILLS_TABLE_END -->

</skills_system>
