# McAlbum

McAlbum 是一个以“世界档案馆”为定位的 Minecraft Fabric 纯净生存服务器展示项目。

## 当前阶段

- Nuxt 前端负责静态生成与少量 Vue 交互；
- 结构化内容存放在根目录 `content/` 中，格式统一为 JSON；
- FastAPI 目录已经预留，目前只提供健康检查骨架；
- 后续生产数据库使用 MySQL，图片使用本地持久化文件系统；
- 详细设计见 `docs/`。

## 前端

前端要求 Node.js 22.22.3 或更高兼容版本，推荐使用仓库 `.nvmrc` 中记录的版本。

```powershell
npm install
npm run dev:web
```

常用检查：

```powershell
npm run typecheck:web
npm run test:web
npm run generate:web
```

首次运行浏览器验收前安装项目工具依赖和 Chromium：

```powershell
python -m pip install -r requirements-tools.txt
python -m playwright install chromium
```

完整开发质量门禁会依次运行内容校验、类型检查、单元测试、静态生成、产物扫描和浏览器验收：

```powershell
npm run check:web
```

当前静态浏览路径包括：

- `/`：世界首页；
- `/album`：相册与 URL 标签筛选；
- `/photos/:id`：照片详情；
- `/stories` 与 `/stories/:id`：历史作品集及专题详情；
- `/players` 与 `/players/:id`：只公开已获许可记录的玩家列表与详情。

部署前在环境变量中将 `NUXT_PUBLIC_SITE_URL` 设置为正式站点根地址。该值用于 Canonical、Open Graph、`sitemap.xml` 和 `robots.txt`；默认的 `http://localhost:3000` 仅供本地开发。

## 内容校验

```powershell
npm run validate:content
```

发布前运行更严格的检查，阻止 Mock 内容和未经核实的媒体说明进入发布快照：

```powershell
npm run validate:content:release
```

## 媒体导入

参考图片先放在导入来源目录，再通过清单一次性导入；页面不得直接引用来源目录：

```powershell
npm run import:media
```

导入工具会计算 SHA-256 去重，把无损原图复制到 `storage/originals`，在 `storage/variants` 生成响应式 WebP，并在 `content/media-assets` 写入媒体清单。来源文件不会被自动删除。

前端运行、检查和构建前会执行 `npm run sync:public-content`，生成浏览器安全的媒体与内容投影，并同步生成站点地图与 robots 文件。内容投影会移除私密玩家和隐藏评论；媒体投影不包含原图路径、文件名、哈希或内部编辑状态。`apps/web/app/generated/` 下的投影文件均不应手工编辑。

## 正式发布门禁

配置正式 `NUXT_PUBLIC_SITE_URL` 并确认内容后运行：

```powershell
npm run check:release
```

该命令会拒绝 Mock、非 `published` 内容、未经核实的媒体说明和仍指向 localhost 的站点元信息。通过后会在 `apps/web/.output/release-manifest.json` 生成源内容与公开产物的 SHA-256 清单；部署时发布 `apps/web/.output/public`，并把清单与对应原图备份一同归档。

当前内容仍是待确认草稿，所以 `check:release` 按设计不会通过；日常开发请使用 `check:web`。

## FastAPI 骨架

在 `apps/api` 下创建虚拟环境并安装开发依赖：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

API 默认地址为 `http://127.0.0.1:8000/api/health`。

### 玩家协作与管理端

玩家协作阶段需要同时运行 MySQL、FastAPI 和 Nuxt。首次启用时，在仓库根目录复制并调整 `.env.example`，然后执行：

```powershell
# 1. 准备 API 依赖
cd apps/api
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
cd ../..

# 2. 升级 MySQL 结构
npm run api:migrate

# 3. 创建首个管理员（密码通过隐藏输入读取）
cd apps/api
.\.venv\Scripts\python.exe -m app.cli create-admin --username admin --display-name "档案管理员"

# 4. 将现有 JSON 内容幂等导入数据库
.\.venv\Scripts\python.exe -m app.cli import-content --owner admin
```

分别启动后端与前端：

```powershell
# 终端一
cd apps/api
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload

# 终端二（仓库根目录）
npm run dev:web
```

浏览器访问 `http://localhost:3000/manage/login`。管理员可创建一次性邀请码；普通用户根据已授予能力维护本人档案、上传照片、建立散图与作品集草稿并提交审核。管理员可审核发布、调整权限、停用账号以及隐藏或恢复评论。

照片或作品集进入 `published` 状态后，公开列表和详情会在浏览器刷新时通过 FastAPI 读取最新内容，不需要重新启动或重新构建 Nuxt。静态 JSON 仍作为首屏和 API 故障兜底；管理员的“同步并重建”只用于更新 SEO 页面和归档快照。

开发环境默认不允许 API 直接执行静态重建。需要生成归档快照时，确认部署目录与备份策略后再把 `MCALBUM_ENABLE_BUILD_TRIGGER` 设为 `true`；生产环境还必须启用 HTTPS，并把 `MCALBUM_COOKIE_SECURE` 设为 `true`。

生产环境建议将 `NUXT_PUBLIC_API_BASE` 构建为同源 `/api`，并参考 `deploy/nginx/mcalbum.conf.example`：Nginx 需要代理 FastAPI、把 `/media/` 映射到持久化的 `storage/variants`，并把不存在的页面路径回退到 Nuxt 生成的 `200.html`。因此新发布照片和作品集的详情路由都不依赖静态重建。

## MySQL 开发服务

复制 `.env.example` 为 `.env`，根据本机环境调整密码后运行：

```powershell
docker compose up -d mysql
```

静态快照可以脱离 MySQL 浏览；启用玩家投稿后，最新公开内容、登录和管理功能需要 FastAPI 与 MySQL 持续运行。

## 依赖安全说明

当前 Nuxt 4.6.2 的构建链会经 Nitro/listhen 间接安装 `node-forge@1.4.0`。npm 安全公告已将该版本标记为高风险，但截至项目初始化时 npm 尚无更高修复版本可安装。

- 不要把 `nuxt dev` 或预览服务暴露到公网；
- 生产环境只部署 `apps/web/.output/public` 静态产物；
- 后续升级依赖时重新运行 `npm audit`，上游修复可用后及时更新锁文件。
