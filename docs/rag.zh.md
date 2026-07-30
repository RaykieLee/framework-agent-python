# RAG(检索增强生成)

本文档描述脚手架中可用的 RAG(检索增强生成)功能。

## 概览

脚手架提供一条完整的 RAG 管线，用于基于文档的知识检索：

- **文档处理**:解析 PDF、DOCX、TXT 和 MD 文件
- **嵌入**:使用 OpenAI、Voyage AI 或 Sentence Transformers 把文本转换为向量
- **向量存储**:Milvus 向量数据库，用于相似度检索
- **检索**:语义搜索，可选重排序
- **智能体集成**:AI 智能体可调用 RAG 工具

## 快速开始

在项目创建时启用 RAG:

```bash
# Interactive wizard
fastapi-fullstack new

# With RAG enabled
fastapi-fullstack create my_project --enable-rag

# Full RAG with all features
fastapi-fullstack create my_project --enable-rag --pdf-parser llamaparse --reranker cohere
```

---

## 架构

```
┌─────────────────────────────────────────────────────────────┐
│                     Document Sources                         │
│          (Upload API, Google Drive, File System)            │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    Document Parsers                          │
│    (PDF: PyMuPDF/LlamaParse, DOCX, TXT, MD)                  │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                  Chunking (Recursive)                        │
│            (Default: 512 chars, 50 overlap)                 │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   Embedding Providers                        │
│     (OpenAI, Voyage AI, Sentence Transformers)              │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   Vector Store (Milvus)                      │
│              Similarity Search (Cosine)                     │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    Retrieval API                             │
│              Search, Filter, Rerank                         │
└─────────────────────────────────────────────────────────────┘
```

---

## 配置

### 环境变量

```bash
# Required for Milvus
MILVUS_URI=localhost:19530
MILVUS_TOKEN=

# Optional - Embedding Provider
OPENAI_API_KEY=sk-...        # For OpenAI embeddings
VOYAGE_API_KEY=...           # For Voyage AI embeddings

# Optional - PDF Parser
LLAMA_CLOUD_API_KEY=...      # For LlamaParse

# Optional - Reranker
COHERE_API_KEY=...           # For Cohere reranker
HF_TOKEN=...                # For HuggingFace Cross-Encoder reranker
CROSS_ENCODER_MODEL=...    # Model name (default: cross-encoder/ms-marco-MiniLM-L6-v2)
```

### 配置选项

| 选项 | 取值 | 说明 |
|--------|--------|-------------|
| `enable_rag` | bool | 启用 RAG 功能 |
| `embedding_provider` | 自动推导 | 嵌入模型服务商(从 LLM 服务商自动推导：OpenAI→openai、Anthropic→voyage、OpenRouter→sentence_transformers) |
| `pdf_parser` | `pymupdf`、`llamaparse` | PDF 解析方式(通过 `--pdf-parser` CLI 标志设置) |
| `enable_reranker` | bool | 启用重排序(通过 `--reranker` CLI 标志设置：none/cohere/cross_encoder) |

---

## 文档处理

### 支持的文件类型

| 格式 | 扩展名 | 解析器 |
|--------|-----------|--------|
| PDF | `.pdf` | PyMuPDF(默认)或 LlamaParse |
| Word | `.docx` | python-docx |
| Markdown | `.md` | Python 原生 |
| Text | `.txt` | Python 原生 |

### 分块配置

[`app/rag/config.py`](backend/app/rag/config.py) 中的默认设置：

```python
class RAGSettings(BaseModel):
    chunk_size: int = 512       # Characters per chunk
    chunk_overlap: int = 50     # Overlap between chunks
```

---

## 嵌入服务商

### OpenAI 嵌入

默认使用 `text-embedding-3-small`(1536 维)。

```python
from app.rag.embeddings import EmbeddingService

service = EmbeddingService(settings)
vector = service.embed_query("your search query")
```

### Voyage AI

使用 `voyage-3`(1024 维)—— 针对检索任务优化。

### Sentence Transformers

使用 `all-MiniLM-L6-v2`(384 维)做本地嵌入。无需 API。

---

## 重排序

重排序通过专用重排序模型对初始向量检索结果重新排序，从而提升检索质量。通过 `--reranker` CLI 标志启用。

### Cohere 重排序器

使用 Cohere 的 rerank API。需要 `COHERE_API_KEY`。

```bash
fastapi-fullstack create my_project --enable-rag --reranker cohere
```

### Cross-Encoder 重排序器

在本地使用 HuggingFace Cross-Encoder 模型。私有模型需要 `HF_TOKEN`(公开模型可选)。

```bash
fastapi-fullstack create my_project --enable-rag --reranker cross_encoder
```

默认模型：`cross-encoder/ms-marco-MiniLM-L6-v2`。可用 `CROSS_ENCODER_MODEL` 环境变量覆盖。

### 在 API 中使用重排序

调用检索端点时，把 `use_reranker=true` 作为查询参数传入：

## API 端点

所有 RAG 端点都以 `/api/v1/rag` 为前缀。

### 上传文档

```http
POST /api/v1/rag/collections/{name}/upload
Content-Type: multipart/form-data

file: <document>
```

### 检索文档

```http
POST /api/v1/rag/search
Content-Type: application/json

{
  "query": "search term",
  "collection_name": "documents",
  "limit": 5,
  "min_score": 0.0,
  "filter": ""
}
```

**查询参数：**

| 参数 | 类型 | 默认值 | 说明 |
|-----------|------|---------|-------------|
| `use_reranker` | bool | false | 是否使用重排序(若已配置) |

**注意：** 设置 `use_reranker=true` 即可在检索时启用重排序。重排序必须在项目配置中启用(通过 `--reranker cohere` 或 `--reranker cross_encoder` CLI 标志)。

### 列出集合

```http
GET /api/v1/rag/collections
```

### 获取集合信息

```http
GET /api/v1/rag/collections/{name}/info
```

### 创建集合

```http
POST /api/v1/rag/collections/{name}
```

### 删除集合

```http
DELETE /api/v1/rag/collections/{name}
```

### 删除文档

```http
DELETE /api/v1/rag/collections/{name}/documents/{document_id}
```

---

## AI 智能体集成

RAG 通过 `search_knowledge_base` 工具与 AI 智能体集成。

### PydanticAI 智能体

```python
# app/agents/tools/rag_tool.py
from app.agents.tools.rag_tool import search_knowledge_base

# Use in your agent tools
result = await search_knowledge_base(
    query="What is the project about?",
    collection="documents",
    top_k=5
)
```

### 可用工具

| 函数 | 说明 |
|----------|-------------|
| `search_knowledge_base` | 异步检索函数 |

### 工具定义

```python
{
    "name": "search_knowledge_base",
    "description": "Search the knowledge base and return formatted results",
    "parameters": {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "The search query string"},
            "collection": {"type": "string", "description": "Name of the collection to search"},
            "top_k": {"type": "integer", "description": "Number of top results to retrieve"}
        },
        "required": ["query"]
    }
}
```

---

## 定时任务

RAG 的导入可以通过后台任务 worker 来定时执行：

### 任务配置

在 [`app/worker/tasks/schedules.py`](backend/app/worker/tasks/schedules.py) 中：

```python
@scheduler.scheduled("interval", hours=24)
async def rag_ingestion_task():
    """Daily RAG ingestion from configured sources."""
    # Implements periodic document sync
```

---

## CLI 命令

### 上传文档

```bash
# Upload a document to a collection
python -m app.commands.rag upload --collection my_docs --path ./document.pdf

# Batch upload
python -m app.commands.rag upload --collection my_docs --path ./docs/
```

### 列出集合

```bash
python -m app.commands.rag list-collections
```

---

## 前端集成

前端在 [`frontend/src/lib/rag-api.ts`](frontend/src/lib/rag-api.ts) 包含 RAG API 客户端：

```typescript
import { ragApi } from '@/lib/rag-api';

// Upload document
await ragApi.uploadDocument(collection, file);

// Search
const results = await ragApi.searchDocuments({
  query: 'search query',
  collection_name: 'documents',
  limit: 5
});
```

---

## 重排序

用重排序改善检索结果：

### Cohere 重排序器

```bash
fastapi-fullstack create my_project --enable-rag --enable-reranker cohere
```

### Cross-Encoder 重排序器

在本地使用 Sentence Transformers:

```bash
fastapi-fullstack create my_project --enable-rag --enable-reranker cross_encoder
```

---

## Google Drive 集成

启用 Google Drive 作为文档来源：

```bash
fastapi-fullstack create my_project --enable-rag --enable-google-drive-ingestion
```

需要在 Google Cloud Console 中配置 OAuth2。

---

## 环境变量参考

| 变量 | 是否必填 | 说明 |
|----------|----------|-------------|
| `MILVUS_URI` | 是 | Milvus 连接 URI |
| `MILVUS_TOKEN` | 否 | Milvus 认证令牌 |
| `OPENAI_API_KEY` | OpenAI 嵌入需要 | OpenAI API 密钥 |
| `VOYAGE_API_KEY` | Voyage 嵌入需要 | Voyage AI API 密钥 |
| `LLAMA_CLOUD_API_KEY` | LlamaParse 需要 | LlamaCloud API 密钥 |
| `COHERE_API_KEY` | Cohere 重排序器需要 | Cohere API 密钥 |

---

## 疑难排查

### Milvus 连接问题

确保 Milvus 正在运行：

```bash
docker run -d -p 19530:19530 milvusdb/milvus
```

### 嵌入模型加载失败

对于 Sentence Transformers,检查模型缓存目录的权限：

```python
from app.core.config import settings
print(settings.MODELS_CACHE_DIR)
```

### 文档解析错误

- **PDF 没有文本**:对扫描件使用 LlamaParse
- **大文件**:在 RAGSettings 中增大分块大小
