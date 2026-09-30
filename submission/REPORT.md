# Báo cáo cá nhân — K4-L3B Day 13 Monitoring & LLMOps

> Mỗi học viên hoàn thiện một file duy nhất này. Khi dẫn evidence, dùng đường dẫn tương đối, ví dụ `evidence/07-trace-waterfall.png`.

## 1. Thông tin học viên

- **Họ và tên:** Mai Tiến Huy
- **MSSV:** 2A202602914
- **Lớp:** K4-L3B
- **Repository URL:** `https://github.com/MaiTienHuy/K4-L3-Day13-MaiTienHuy-2A202602914-Monitoring-LLMOps`
- **Commit SHA cuối:** `c71dfcb` (hoặc commit SHA hiển thị trên GitHub sau khi push)
- **Challenge ID:** `day13-k4-l3b-monitoring-llmops-v1`
- **Tên project Langfuse cá nhân:** `day13-k4-l3b-2A202602914`

## 2. Evidence index

Điền đúng đường dẫn tới evidence thực tế. Có thể đổi tên hoặc dùng nhiều ảnh nếu cần.

| Evidence | Đường dẫn |
|---|---|
| Pytest cuối | `evidence/01-pytest.png` |
| Log validator | `evidence/02-log-validator.png` |
| Dashboard validator | `evidence/03-dashboard-validator.png` |
| Structured log | `evidence/04-structured-log.png` |
| PII redaction | `evidence/05-pii-redaction.png` |
| Trace list | `evidence/06-trace-list.png` |
| Trace waterfall | `evidence/07-trace-waterfall.png` |
| Trace metadata | `evidence/08-trace-metadata.png` |
| Prompt versions | `evidence/09-prompt-versions.png` |
| Prompt rollback | `evidence/10-prompt-rollback.png` |
| Dashboard runtime | `evidence/11-dashboard-overview.png` |
| Incident metric | `evidence/12-incident-metric.png` |
| Incident log | `evidence/13-incident-log.png` |
| Incident trace | `evidence/14-incident-trace.png` |

## 3. Kết quả kỹ thuật

| Nội dung | Baseline | Kết quả cuối | Nhận xét |
|---|---|---|---|
| `validate_logs.py` | 60/100 | 100/100 | Đạt toàn bộ 4/4 tiêu chí: JSON schema, Correlation ID propagation, Enrichment, PII scrubbing |
| `validate_dashboard.py` | 0/6 | 6/6 | Hợp lệ toàn bộ 6/6 panel theo contract `config/dashboard.yaml` |
| `pytest` | 16 passed | 24 passed (100%) | Vượt qua toàn bộ unit test bao gồm logging, middleware, PII regex (CCCD, thẻ tín dụng), prompt management |
| Số traces hợp lệ | 0 | 25+ traces | Đã đẩy đủ traces với đầy đủ root trace, retrieval observation, generation observation lên Langfuse Cloud |
| Số PII leak | 4 | 0 | Scrub thành công email, phone, CCCD 12 số, thẻ tín dụng 13-19 số |
| Latency P95 / TTFT P95 | 154ms / 50ms | 153.5ms / 50.0ms | Bình thường đạt P95 ~153.5ms; khi có incident `rag_slow` P95 đạt đỉnh 3442.5ms |
| Retrieval success rate | 100% | 100% | Toàn bộ 26 request đều thực thi retrieval thành công |

## 4. Logging và PII

- **Cách tạo/nhận và truyền correlation ID:** Trong middleware `CorrelationIdMiddleware` (`app/middleware.py`), request đến được kiểm tra header `X-Correlation-ID` hoặc `X-Request-ID`. Nếu hợp lệ theo định dạng `req-[0-9a-f]{8}`, middleware tái sử dụng; nếu không có hoặc sai format, sinh mới bằng `f"req-{uuid.uuid4().hex[:8]}"`. Correlation ID được gán vào `contextvars` và tự động trả về client qua response header `X-Request-ID`.
- **Các metadata được ghi vào structured log:** Bao gồm các trường hệ thống và ngữ cảnh: `service`, `event`, `level`, `ts`, `correlation_id`, `user_id_hash` (SHA-256 12 ký tự), `session_id`, `feature`, `model`, `env`, `latency_ms`, `ttft_ms`, `tokens_in`, `tokens_out`, `cost_usd`, `quality_score`, `tool_name`, `tool_success`, `trace_id`.
- **Cách bảo đảm PII được scrub trước khi ghi:** Processor Structlog `scrub_event` trong `app/logging_config.py` duyệt đệ quy qua toàn bộ event dictionary trước khi render thành JSON. Bằng các regex biên dịch sẵn, processor thay thế:
  - Email: `[EMAIL_REDACTED]`
  - Số điện thoại VN (+84/0): `[PHONE_REDACTED]`
  - CCCD (12 chữ số): `[CCCD_REDACTED]`
  - Thẻ tín dụng (13 đến 19 chữ số): `[CARD_REDACTED]`
- **Cách kiểm chứng kết quả:** Chạy `python -m pytest tests/test_pii.py` và `python scripts/validate_logs.py`. Kết quả xác nhận 0 PII leak detected và điểm đạt 100/100.

## 5. Tracing và prompt versioning

- **Cách xác nhận traces do chính tôi tạo trong project cá nhân:** Traces được ghi trực tiếp vào project Langfuse mang tên `day13-k4-l3b-2A202602914` thông qua API Keys cá nhân. Các trace ID xuất hiện trên UI Langfuse hoàn toàn trùng khớp với `trace_id` và `correlation_id` được ghi trong `data/logs.jsonl` khi chạy workload local.
- **Cấu trúc root/retrieval/generation observations:**
  - Root Trace: `day13-agent-request` bọc toàn bộ request xử lý của agent.
  - Span con `retrieval` (type: retriever): Instrumented thông qua decorator `@observe(name="retrieval", as_type="retriever")` trong `app/mock_rag.py`.
  - Span con `generation` (type: generation): Instrumented qua `@observe(name="generation", as_type="generation")` trong `app/mock_llm.py`, ghi nhận `model`, `usage_details` (`input`, `output`, `total`), và `cost_details`.
- **Cách nối trace với log:** Trường `correlation_id` (`req-<8-hex>`) được truyền vào metadata của trace trên Langfuse, đồng thời trường `trace_id` của Langfuse được lưu ngược lại vào structured log `response_sent`.
- **Prompt name:** `day13-chat`
- **Version/label baseline:** Version 1 (label: `baseline`, `production`)
- **Version/label candidate:** Version 2 (label: `candidate`)
- **Trace ID của mỗi version:**
  - Baseline (v1, production ban đầu): `473883a440633529e5ab241c8c9840aa` (Correlation ID: `req-9642ce86`)
  - Candidate (v2, sau khi promote lên production): `e9c856d2ba8d7807555f92ecf4ae13ae` (Correlation ID: `req-f8526962`)
  - Rollback (v1, sau khi rollback production về v1): `d0f27c75e24d8979f78610e37ea90531` (Correlation ID: `req-fcf4e733`)
- **Cách promote và rollback `production`:**
  - Promote: Trên Langfuse Web UI, chọn Prompt `day13-chat`, mở Version 2 và gán nhãn `production` thay thế cho Version 1.
  - Rollback: Chọn lại Version 1, gán nhãn `production` để chuyển lưu lượng sản xuất trở lại phiên bản ổn định đã được kiểm chứng.

## 6. Dashboard, SLO và alerts

- **Dashboard và sáu panel:** Xây dựng runtime dashboard tại `http://127.0.0.1:8000/dashboard` tương thích với `config/dashboard.yaml` gồm 6 panels:
  1. *Latency percentiles and TTFT* (đơn vị: ms, hiển thị P50, P95, TTFT P95 kèm ngưỡng đỏ 3000ms).
  2. *Request traffic* (đơn vị: req/min, tần suất request).
  3. *Error rate and retrieval success* (đơn vị: %, hiển thị % lỗi và % retrieval thành công kèm ngưỡng 90%).
  4. *Cost over time* (đơn vị: USD, tổng chi phí tích luỹ).
  5. *Input and output tokens* (đơn vị: tokens, số lượng token in/out).
  6. *Quality proxy* (đơn vị: score 0-1, điểm chất lượng phản hồi trung bình).
- **SLO và lý do chọn:**
  - Latency: P95 <= 2000ms nhằm đảm bảo trải nghiệm tương tác trực tuyến không bị giật lag.
  - Error rate: <= 1.0% để duy trì độ tin cậy dịch vụ.
  - Retrieval success rate: >= 95.0% đảm bảo hệ thống RAG luôn có context hỗ trợ trả lời.
- **Cách tính error budget:** Mục tiêu SLO 99.5% trong 28 ngày tương đương error budget 0.5%. Nếu hệ thống phục vụ 10,000 request, tối đa cho phép 50 request bị lỗi hoặc chậm hơn ngưỡng quy định.
- **Ba alert và runbook tương ứng:**
  - `HighLatencyP95`: P95 > 2000ms kéo dài trong 5 phút. Runbook tại `docs/alerts.md#alert-1-highlatencyp95`.
  - `HighErrorRate`: Error rate > 5% trong 5 phút. Runbook tại `docs/alerts.md#alert-2-higherrorrate`.
  - `LowRetrievalSuccess`: Retrieval success rate < 90% trong 5 phút. Runbook tại `docs/alerts.md#alert-3-lowretrievalsuccess`.

## 7. Điều tra challenge

- **Challenge ID:** `day13-k4-l3b-monitoring-llmops-v1`
- **Khoảng thời gian điều tra:** 16:44:40 - 16:45:00 (+07:00) / 09:44:40 - 09:45:00 UTC
- **Triệu chứng từ metrics:** Dashboard panel 1 (*Latency percentiles and TTFT*) vọt lên trạng thái **VIOLATION** với P95 đạt **3442.5ms**, vượt xa ngưỡng threshold đỏ 3000ms và SLO 2000ms. Trong khi đó, TTFT vẫn duy trì ở mức 50ms và Error rate vẫn là 0%.
- **Log line và correlation ID liên quan:** Lọc `data/logs.jsonl` phát hiện request `response_sent` bất thường:
  - `correlation_id`: `req-4480fd35`
  - `latency_ms`: 2652ms
  - `feature`: `monitoring`
  - `tool_name`: `retrieval`
  - `user_id_hash`: `68e37dc7cb5e`
  - `ts`: `2026-09-30T09:44:58.564958Z`
- **Trace ID và span gây ảnh hưởng:** Mở trace `42954a710f75db51d048a50b8f16ec8c` (có cùng `correlation_id: req-4480fd35`) trên Langfuse, quan sát cây waterfall xác định span `retrieval` bị chậm bất thường, chiếm tới **2500ms** (2.50s) trên tổng thời gian 2.65s của request. Span `generation` chỉ mất ~150ms.
- **Root cause:** Kịch bản incident `rag_slow` được kích hoạt trên feature `monitoring`. Trong logic `app/mock_rag.py`, hàm `retrieve()` bị chèn độ trễ nhân tạo 2.5s khi gặp feature `monitoring`, mô phỏng sự cố mạng hoặc nghẽn cơ sở dữ liệu vector/retriever downstream.
- **Fix action:** Chạy lệnh khắc phục `python scripts/inject_incident.py --disable` để tắt cờ sự cố `rag_slow`. Trong thực tế, restart/scale-out vector database hoặc bật bộ nhớ đệm cache kết quả truy vấn.
- **Preventive measure:**
  1. Cấu hình timeout nghiêm ngặt (1500ms) cho retriever và kích hoạt circuit breaker khi vector DB chậm.
  2. Bật alert `HighLatencyP95` để phát hiện suy giảm hiệu năng trước khi vi phạm toàn bộ error budget.
  3. Bổ sung fallback answering khi retrieval bị timeout.

## 8. Giải thích và tự đánh giá

- **Một quyết định kỹ thuật quan trọng và lý do:** Quyết định phân tách rõ ràng trách nhiệm giữa `CorrelationIdMiddleware` (chịu trách nhiệm trích xuất/sinh correlation ID và gán response header) và `enrich_contextvars` trong router (bổ sung user, feature, model). Điều này đảm bảo correlation ID luôn tồn tại ngay cả khi request bị lỗi từ tầng routing hoặc serialization.
- **Một lỗi/blocker đã gặp:** Khi tích hợp Langfuse SDK phiên bản mới trên môi trường Windows, một số request bị ảnh hưởng độ trễ do kết nối timeout mặc định ngắn tới API public v2 observations.
- **Cách tìm nguyên nhân và xử lý:** Đã cấu hình timeout tường minh `httpx/langfuse` lên 30s và bảo đảm decorator `@observe` bắt lỗi ngoại lệ mềm để không bao giờ làm gián đoạn luồng trả lời người dùng.
- **Cách hiểu luồng Metrics → Logs → Traces:** Metrics là tín hiệu cảnh báo đầu tiên giúp phát hiện triệu chứng (What/When) -> Logs thu hẹp phạm vi điều tra và cung cấp Correlation ID của các request lỗi (Where/Who) -> Traces đi sâu vào cây thực thi phân tán để cô lập chính xác span bị lỗi hoặc thắt cổ chai (Why).
- **Vai trò của prompt version, token/cost, SLO hoặc rollback trong vận hành LLM:** Quản lý phiên bản prompt và kiểm soát chi phí token là cốt lõi của LLMOps. Khi một bản cập nhật prompt vô tình làm tăng chi phí hoặc giảm chất lượng, cơ chế rollback nhãn `production` cho phép đưa hệ thống về trạng thái ổn định ngay lập tức mà không cần triển khai lại mã nguồn.
- **Điều quan trọng nhất đã học:** Nắm vững trọn vẹn kiến trúc Observability trong thực tế: từ Structured Logging, Redaction PII bảo vệ quyền riêng tư, đến Distributed Tracing và thiết lập Dashboard cảnh báo theo chuẩn SLO/SLI.
- **Hạn chế hoặc phần chưa hoàn thành, nếu có:** Bài làm đã hoàn thành 100% tất cả các checkpoint và bài tập thử thách CP1, CP2, CP3, CP4.

## 9. Checklist trước khi nộp

- [x] Kết quả và evidence thuộc commit SHA cuối.
- [x] Tất cả ảnh/output mở được bằng đường dẫn tương đối.
- [x] Incident evidence nối đúng metric → log → trace.
- [x] Trace/prompt evidence thuộc project Langfuse cá nhân và ảnh không lộ key/secret.
- [x] Repository chạy lại được theo README.
- [x] Không có secret, API key, PII thô hoặc evidence của người khác/lớp khác.
- [x] URL repo và commit SHA cuối đã được nộp trên LMS/Codelabs.
