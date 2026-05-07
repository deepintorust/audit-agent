# audit-agent

基于“资料文件上传 → 异步流水线处理 → MySQL/Qdrant/S3” 的审计资料预处理服务。

## 本地启动（Docker Compose）

1) 复制并按需修改 `.env`

2) 启动：

```bash
docker compose up -d --build
```

服务：
- API: `http://localhost:8000`
- RabbitMQ 管理台: `http://localhost:15672`
- RustFS Console: `http://localhost:9001`
- Qdrant: `http://localhost:6333`

## API

- `POST /api/v1/files/upload`：上传文件 + 表单字段（project/company/phase/category/subcategory），返回 `file_id/run_id`
- `GET /api/v1/files/{file_id}/status`：查询流水线状态与步骤详情

## 流水线（RabbitMQ）

队列（每步一个 worker，可水平扩容）：
- `doc.store.q` → `doc.parse.q` → `doc.extract.q` → `doc.fuse.q` → `doc.chunk.q` → `doc.embed.q` → `doc.index.q`

每个队列自动声明：
- `*.dlq`：死信队列
- `*.retry.60s / *.retry.600s`：TTL 延迟重试队列

## 数据库初始化

Compose 启动 MySQL 时会执行 `scripts/init_mysql.sql` 初始化表结构。

对象存储 bucket 会在首次上传时由服务自动创建（幂等）。

## Prompt 管理（推荐）

把提示词放到项目根目录 `prompts/` 下（支持 Markdown），通过 `.env` 的 `EXTRACT_PROMPT_TEMPLATE_PATH` 指向容器内挂载路径：

- 宿主机：`prompts/extract_prompt.md`
- 容器内：`/etc/audit-agent/prompts/extract_prompt.md`
