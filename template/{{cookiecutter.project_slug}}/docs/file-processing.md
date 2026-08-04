# 文件处理

本文档介绍文件在两种场景下的处理方式：聊天文件上传（面向用户）和 RAG 文档摄取（管理员/CLI）。

{%- if cookiecutter.use_jwt %}

## 聊天文件上传

当用户在聊天界面上传文件时，执行以下流水线：

### 流程

```
1. Upload     POST /api/v1/files/upload
               |
2. Validate    Check MIME type against allowed list + enforce size limit
               |
3. Classify    Determine file_type: "image", "pdf", "docx", "text"
               |
4. Parse       Extract text content (images skip this step)
               |
5. Store       Save file to media/{user_id}/ via FileStorageService
               |
6. Record      Create ChatFile row in database
               |
7. Link        When message is sent, ChatFile is attached via message_id FK
               |
8. Display     Frontend shows images as thumbnails, documents as badges
```

### 支持的文件类型

| Category | MIME 类型 | 扩展名 | 处理方式 |
|----------|-----------|------------|------------|
| **Images** | image/jpeg, image/png, image/webp, image/gif | .jpg, .png, .webp, .gif | Stored as-is. Sent to LLM as `BinaryContent` for vision analysis. |
| **PDF** | application/pdf | .pdf | Text extracted via configured PDF parser. Appended to prompt as context. |
| **DOCX** | application/vnd.openxmlformats-officedocument.wordprocessingml.document | .docx | Paragraphs extracted via `python-docx`. Appended to prompt as context. |
| **Text** | text/plain, text/markdown | .txt, .md | UTF-8 decoded directly. Appended to prompt as context. |

### PDF 解析器选择（聊天）

{%- if cookiecutter.use_all_pdf_parsers %}

The `CHAT_PDF_PARSER` environment variable controls which parser processes PDFs
uploaded in chat. This is separate from the RAG ingestion parser (`PDF_PARSER`).

| 解析器 | `CHAT_PDF_PARSER=` | 要求 | 速度 | 质量 |
|--------|-------------------|--------------|-------|---------|
| PyMuPDF | `pymupdf`（默认）| 无需（已内置）| 快速 | 适合文本密集型 PDF |
| LlamaParse | `llamaparse` | `LLAMAPARSE_API_KEY` | 慢（API 调用）| 最适合复杂布局 |
| LiteParse | `liteparse` | 无需 | 中等 | 良好的平衡 |

If the selected parser fails, it automatically falls back to PyMuPDF.

{%- elif cookiecutter.use_llamaparse %}

PDFs are processed using LlamaParse (AI-powered parsing). Requires the
`LLAMAPARSE_API_KEY` environment variable. Falls back to basic text extraction
if the API is unavailable.

{%- else %}

PDFs are processed using PyMuPDF. This is a local parser that requires no API
key and handles text extraction, table detection, and block-level parsing.

{%- endif %}

### 大小限制

- Maximum file size: `MAX_UPLOAD_SIZE_MB` environment variable (default: **50 MB**)
- The limit is enforced server-side after reading the file content.

### 存储

Files are saved by `FileStorageService` to the `media/` directory:

```
media/
  {user_id}/
    document.pdf
    screenshot.png
    ...
```

{%- if cookiecutter.enable_file_storage %}
If S3/MinIO storage is configured (`S3_ENDPOINT`), files are uploaded to the
configured bucket instead of local disk.
{%- endif %}

### ChatFile 模型

The `ChatFile` database model tracks uploaded files:

| 字段 | 类型 | 说明 |
|-------|------|-------------|
| `id` | UUID | 主键 |
| `user_id` | UUID/FK | 所有者（用于访问控制）|
| `filename` | String | 原始文件名 |
| `mime_type` | String | MIME 类型（例如 `application/pdf`）|
| `size` | Integer | 文件大小（字节）|
| `storage_path` | String | 存储中的相对路径 |
| `file_type` | String | 分类类型：`image`、`pdf`、`docx`、`text` |
| `parsed_content` | Text | 提取的文本内容（图片为 NULL）|
| `message_id` | UUID/FK | 关联的消息（发送消息时设置）|
| `created_at` | DateTime | 上传时间戳 |

### 所有权与访问

- Only the file owner can download their files (`GET /files/{id}`).
- The `FileUploadService.get_user_file()` method compares `chat_file.user_id`
  against the requesting user's ID. Returns `NotFoundError` on mismatch.
- There is no admin override -- admins cannot access other users' chat files
  through the file API.

{%- endif %}

{%- if cookiecutter.enable_rag %}

## RAG 文档摄取

当文档被摄取到 RAG 知识库（通过 CLI 或 API）时，另一个流水线处理解析、分块和嵌入。

### 摄取流程

```
1. Input       File path (CLI) or uploaded file (API)
                |
2. Parse       DocumentProcessor selects parser by file type
                |
3. Chunk       Text split into segments (configurable size/overlap/strategy)
                |
4. Embed       Chunks embedded via configured provider
                |
5. Store       Vectors written to vector database
                |
6. Track       RAGDocument record created in SQL (status tracking)
```

### 支持的格式

The set of supported formats depends on the configured PDF parser:

{%- if cookiecutter.use_all_pdf_parsers or cookiecutter.use_llamaparse %}

**LlamaParse** supports 130+ formats including PDF, DOCX, XLSX, PPTX, HTML,
CSV, RTF, and many more.

**PyMuPDF** supports a smaller set: PDF, TXT, MD, DOCX, and common text formats.

Use `GET /api/v1/rag/supported-formats` to check what the current configuration
supports at runtime.

{%- else %}

Supported file types with the default PyMuPDF parser:

| Extension | Type | Notes |
|-----------|------|-------|
| `.pdf` | PDF | Text + table extraction via PyMuPDF |
| `.docx` | Word | Paragraph extraction via python-docx |
| `.txt` | Plain text | Direct read |
| `.md` | Markdown | Direct read |

{%- endif %}

### PDF 解析器选择（RAG）

{%- if cookiecutter.use_all_pdf_parsers %}

The `PDF_PARSER` environment variable controls which parser processes PDFs
during RAG ingestion:

| 解析器 | `PDF_PARSER=` | 适用场景 |
|--------|--------------|----------|
| PyMuPDF | `pymupdf`（默认）| 快速本地处理，文本密集型文档 |
| LlamaParse | `llamaparse` | 复杂布局、扫描 PDF、130+ 格式 |
| LiteParse | `liteparse` | 速度与质量的平衡 |

Note: `PDF_PARSER` controls RAG ingestion. `CHAT_PDF_PARSER` controls chat
file uploads. They can be set independently.

{%- elif cookiecutter.use_llamaparse %}

RAG ingestion uses LlamaParse for document parsing. Configure via:
- `LLAMAPARSE_API_KEY` -- Your LlamaParse API key
- `LLAMAPARSE_TIER` -- Parsing tier: `fast`, `cost_effective`, `agentic` (default), `agentic_plus`

{%- else %}

RAG ingestion uses PyMuPDF for document parsing (local, no API key required).

{%- endif %}

### 分块配置

Text is split into chunks before embedding. Configure via environment variables:

| 变量 | 默认值 | 说明 |
|----------|---------|-------------|
| `RAG_CHUNK_SIZE` | `512` | Maximum characters per chunk |
| `RAG_CHUNK_OVERLAP` | `50` | Characters of overlap between chunks |
| `RAG_CHUNKING_STRATEGY` | `recursive` | Strategy: `recursive`, `markdown`, `fixed` |

**Strategy comparison:**

| 策略 | 适用场景 |
|----------|----------|
| `recursive` | 通用文本；按段落、句子、单词依次分割 |
| `markdown` | Markdown/结构化文档；在标题边界处分割 |
| `fixed` | 均匀的块大小；最简单但可能在句子中间分割 |

### 嵌入提供商

{%- if cookiecutter.use_openai_embeddings %}
Embeddings are generated using **OpenAI** (`text-embedding-3-small` by default).
Set `EMBEDDING_MODEL` to change the model.
{%- elif cookiecutter.use_voyage_embeddings %}
Embeddings are generated using **Voyage AI** (`voyage-3` by default).
Set `VOYAGE_API_KEY` and `EMBEDDING_MODEL` to configure.
{%- elif cookiecutter.use_gemini_embeddings %}
Embeddings are generated using **Google Gemini** (`gemini-embedding-exp-03-07`
by default). Supports multimodal embeddings (text + images).
{%- elif cookiecutter.use_sentence_transformers %}
Embeddings are generated locally using **Sentence Transformers**
(`all-MiniLM-L6-v2` by default). No API key needed. Models are cached in
`MODELS_CACHE_DIR`.
{%- endif %}

### 向量存储

{%- if cookiecutter.use_milvus %}
Vectors are stored in **Milvus**. Configure with `MILVUS_HOST`, `MILVUS_PORT`,
`MILVUS_DATABASE`, and `MILVUS_TOKEN`.
{%- elif cookiecutter.use_qdrant %}
Vectors are stored in **Qdrant**. Configure with `QDRANT_HOST`, `QDRANT_PORT`,
and optionally `QDRANT_API_KEY`.
{%- elif cookiecutter.use_chromadb %}
Vectors are stored in **ChromaDB**. By default uses embedded/persistent mode
(data in `CHROMA_PERSIST_DIR`). Set `CHROMA_HOST` for client-server mode.
{%- elif cookiecutter.use_pgvector %}
Vectors are stored in **pgvector** using the existing PostgreSQL database.
No additional services needed.
{%- endif %}

### RAG 是全局的

Collections are shared across **all users**:

- Any authenticated user can search any collection via `POST /rag/search` or
  through the AI agent's RAG tool.
- Only admins can manage collections, upload documents, configure sync sources,
  and view ingestion logs.
- There is no per-user document isolation.

### 文档跟踪


Ingested documents are tracked in the SQL database via the `RAGDocument` model:

| 字段 | 说明 |
|-------|-------------|
| `collection_name` | 目标集合 |
| `filename` | 原始文件名 |
| `filesize` | 文件大小（字节）|
| `filetype` | 文件扩展名（不含点）|
| `status` | `processing`、`done` 或 `error` |
| `error_message` | 错误详情（如果状态为 `error`）|
| `vector_document_id` | 向量存储中的 ID |
| `chunk_count` | 创建的块数 |
| `storage_path` | 原始文件路径（用于重新摄取/下载）|
| `created_at` | 摄取开始时间 |
| `completed_at` | 摄取完成时间 |

Failed ingestions can be retried via `POST /rag/documents/{id}/retry`.


### 同步操作

Sync operations are tracked via the `SyncLog` model, recording source, mode,
total files, ingested/updated/skipped/failed counts, and timing. View sync
history via `GET /rag/sync/logs`.

{%- if cookiecutter.enable_rag_image_description %}

### 图片描述

When processing documents that contain images, the system can optionally
describe images using LLM vision capabilities. Set `RAG_IMAGE_DESCRIPTION_MODEL`
to a vision-capable model (defaults to `AI_MODEL` if empty). The generated
descriptions are included in the document text for better semantic search.

{%- endif %}

{%- if cookiecutter.enable_reranker %}

### 重排

Search results can optionally be reranked for better relevance. Enable
reranking by passing `use_reranker=True` to the search API.
{%- if cookiecutter.use_cohere_reranker %}
Reranking uses Cohere's reranker model. Set `COHERE_API_KEY` to enable.
{%- elif cookiecutter.use_cross_encoder_reranker %}
Reranking uses a cross-encoder model (`CROSS_ENCODER_MODEL`, default:
`cross-encoder/ms-marco-MiniLM-L6-v2`). Runs locally, no API key needed.
{%- endif %}

{%- endif %}
{%- endif %}
