```bash
src/
  app/
    main.py                    # FastAPI入口
    api/
      v1/
        routes_upload.py        # 上传、状态查询、重试触发
        routes_files.py         # 文件详情/切片统计等查询
    deps.py                     # 依赖注入：db、mq、storage、llm、embed、qdrant
    settings.py                 # 从.env加载并校验配置（pydantic-settings）
    logging.py                  # 统一日志格式（run_id/file_id/step/call_id）

  common/
    ids.py                      # hash->short_id、full_hash计算、碰撞校验工具
    time.py
    errors.py                   # 统一错误码：可重试/不可重试
    jsonschema.py               # LLM structured output schema辅助
    retry.py                    # 重试策略（退避、最大次数）
    semaphore.py                # 并发控制（LLM/多模态/embedding）

  domain/
    models.py                   # 领域对象（非ORM）：File/Project/Company/Chunk/Run/Step

  db/
    session.py                  # DB连接/会话
    orm/
      base.py
      file.py                   # file表ORM
      project.py
      company.py
      pipeline_run.py           # pipeline_run表ORM
      process_step.py           # process_step表ORM
      chunk.py                  # chunk表ORM
      llm_call_log.py           # llm_call_log表ORM
    repo/
      file_repo.py              # 幂等写入与首次写入锁定逻辑集中在repo层
      project_repo.py
      company_repo.py
      pipeline_repo.py
      chunk_repo.py
      llm_log_repo.py
    migrations/                 # alembic（如你用）

  mq/
    rabbit.py                   # 连接、声明exchange/queue/dlq/retry队列
    messages.py                 # 消息schema（pydantic）：FileEvent
    publisher.py                # 发布：publish_next(step)
    consumer.py                 # 通用消费框架：ack/nack、重试路由
    topology.py                 # routing_key常量、队列名常量

  storage/
    adapter.py                  # Storage接口：put/get/presign/head
    s3.py                       # S3兼容实现（rustfs/oss）
    local.py                    # 可选：本地存储实现（如果你还保留）

  parser/
    base.py                     # 统一输出结构：DocumentIR（块序列）
    pdf/
      detect.py                 # 判定扫描件/可提取文本
      text_parser.py            # 文本型PDF提取（按页/段落块）
      image_render.py           # PDF按页渲染图片
      multimodal_ocr.py         # 多模态提取每页文本（把每页图片->LLM）
    docx/
      parser.py                 # 保留标题层级：heading_path + paragraph/table块
    xlsx/
      parser.py                 # 每行=sheet+header->value结构化块
    ir.py                       # DocumentIR、Block、TableRow等结构定义

  classifier/
    mapping_loader.py           # 读取外置YAML/JSON映射表（容器外挂载）
    reverse_infer.py            # subcategory -> (phase, category)反推

  llm/
    client.py                   # LLM统一网关：支持structured output/多模态
    schemas/
      extract_chunk.json        # chunk级抽取schema（文件/项目/单位/分类三元组）
      fuse.json                 # 融合schema（唯一化输出）
    prompts/
      extract_chunk.md          # 只放prompt模板（不放schedule/业务流程）
      fuse.md
    call_log.py                 # 记录每次调用到llm_call_log（你要求的粒度）

  extraction/
    chunk_extract.py            # 对单个chunk调用LLM抽取候选
    file_fields.py              # “5属性补空”合并策略（前端优先+反推优先）
    upsert_apply.py             # 首次写入锁定：只补空不覆盖（项目/单位/文件）

  fusion/
    reducer.py                  # Map/Reduce：候选聚合->唯一结果（你要求唯一三元组）

  chunking/
    chunker.py                  # 从DocumentIR切成embedding chunks（递归切分防超长）
    split.py                    # 结构块切分/句子切分/overlap策略

  embedding/
    client.py                   # bge-m3 embedding客户端（批处理）
    batcher.py                  # 攒批、限流、失败重试

  vectorstore/
    qdrant.py                   # collection创建、payload index、upsert
    payload.py                  # payload组装（file_id + 五属性 + chunk_index等）

  workers/
    runner.py                   # worker通用启动（选择消费哪个队列）
    storage_worker.py           # STORE step
    parse_worker.py             # PARSE step
    extract_worker.py           # EXTRACT step（chunk级抽取+落库候选）
    fusion_worker.py            # FUSE step（唯一化+回填三表）
    chunk_worker.py             # CHUNK step（写chunk表）
    embed_worker.py             # EMBED step（写chunk向量状态）
    index_worker.py             # INDEX step（Qdrant upsert）

  scripts/
    init_qdrant.py              # 初始化collection与payload索引（部署时跑一次）
```
