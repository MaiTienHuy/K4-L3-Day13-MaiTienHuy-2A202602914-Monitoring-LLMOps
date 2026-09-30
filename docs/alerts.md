# Template Alert và Runbook

Mỗi alert phải dựa trên triệu chứng người dùng hoặc SLO, không dựa trực tiếp vào tên implementation nội bộ.

## Alert mẫu để tham khảo

Ví dụ dưới đây minh họa mức độ cụ thể cần có. Học viên không cần copy nguyên, nhưng ba alert trong bài nộp nên rõ ràng tương tự: điều kiện là gì, kéo dài bao lâu, ảnh hưởng tới user ra sao và người trực cần kiểm tra gì trước.

- Tên: `HighLatencyP95`
- Severity: `warning`
- Duration: `5m`
- Kênh thông báo: Slack `#k4-l3b-alerts`
- SLI/SLO liên quan: latency P95 của `response_sent.latency_ms`
- Điều kiện và thời gian duy trì: `p95(latency_ms) > 3000ms` trong 5 phút
- Ảnh hưởng tới người dùng: người dùng phải chờ lâu hơn trước khi nhận câu trả lời
- Ba bước kiểm tra đầu tiên:
  1. Mở dashboard latency để xác nhận P95/P99 và khoảng thời gian tăng.
  2. Lọc `data/logs.jsonl` trong khoảng đó, lấy một `correlation_id` có `latency_ms` cao.
  3. Mở trace cùng `correlation_id` trên Langfuse, so sánh các span chính để xác định bước nào bất thường.
- Mitigation tạm thời: dựa trên evidence thực tế để rollback prompt, khôi phục cấu hình liên quan, tắt practice scenario hoặc giảm tải khi demo.
- Owner: `student-<MSSV>`

## Alert 1

- Tên: `HighLatencyP95`
- Severity: `warning`
- Duration: `5m`
- Kênh thông báo: Slack `#k4-l3b-alerts`
- SLI/SLO liên quan: Primary SLO `fast_successful_requests` (SLI: `latency_ms <= 3000ms`)
- Điều kiện và thời gian duy trì: `p95(latency_ms) > 3000ms` liên tục trong 5 phút
- Ảnh hưởng tới người dùng: Người dùng chờ phản hồi lâu bất thường, có nguy cơ timeout request ở phía client
- Ba bước kiểm tra đầu tiên:
  1. **Metrics**: Mở panel Latency trên Dashboard để xác định thời điểm P95/P99 tăng vọt và so sánh với TTFT.
  2. **Logs**: Lọc trong `data/logs.jsonl` các event `response_sent` có `latency_ms > 3000`, lấy một `correlation_id` tiêu biểu.
  3. **Traces**: Mở trace có cùng `correlation_id` trên Langfuse, so sánh thời gian thực thi của span `retrieval` và span `generation` để xác định điểm nghẽn.
- Mitigation tạm thời: Nếu do incident `rag_slow`, tắt incident; nếu do prompt dài gây chậm generation, rollback prompt về version cũ; nếu do quá tải, áp dụng rate limiting tạm thời.
- Owner: `student-MaiTienHuy`

## Alert 2

- Tên: `HighErrorRate`
- Severity: `critical`
- Duration: `3m`
- Kênh thông báo: Slack `#k4-l3b-alerts`
- SLI/SLO liên quan: Guardrail `error_rate_pct_max: 2` (ngưỡng lỗi tối đa 2%)
- Điều kiện và thời gian duy trì: `error_rate_pct > 2%` liên tục trong 3 phút
- Ảnh hưởng tới người dùng: Người dùng nhận lỗi HTTP 500 hoặc không nhận được câu trả lời từ ứng dụng
- Ba bước kiểm tra đầu tiên:
  1. **Metrics**: Kiểm tra panel Errors trên Dashboard để xác nhận tỷ lệ lỗi và thống kê các loại `error_type`.
  2. **Logs**: Lọc các event `request_failed` trong `data/logs.jsonl`, đọc `error_type` và `detail` trong payload, lấy `correlation_id`.
  3. **Traces**: Mở trace cùng `correlation_id` trên Langfuse, kiểm tra observation bị đánh dấu lỗi và xem stacktrace.
- Mitigation tạm thời: Nếu lỗi do vector store (`tool_fail`), tắt incident hoặc restart service; nếu do lỗi parse prompt/model, ngay lập tức rollback phiên bản cấu hình hoặc prompt; bật chế độ fallback trả lời tĩnh.
- Owner: `student-MaiTienHuy`

## Alert 3

- Tên: `LowRetrievalSuccess`
- Severity: `warning`
- Duration: `5m`
- Kênh thông báo: Slack `#k4-l3b-alerts`
- SLI/SLO liên quan: Guardrail `retrieval_success_rate_pct_min: 90` (tỷ lệ retrieval thành công tối thiểu 90%)
- Điều kiện và thời gian duy trì: `retrieval_success_rate_pct < 90%` liên tục trong 5 phút
- Ảnh hưởng tới người dùng: Bot không truy xuất được tài liệu ngữ cảnh chính xác, dẫn đến câu trả lời fallback hoặc chất lượng phản hồi suy giảm
- Ba bước kiểm tra đầu tiên:
  1. **Metrics**: Quan sát tỷ lệ `tool_success_rate_pct` trên panel Errors để xác định mức độ sụt giảm.
  2. **Logs**: Tìm các log có `tool_success == false` hoặc `tool_name == "retrieval"` để xác định query mẫu và `correlation_id`.
  3. **Traces**: Mở trace trên Langfuse, kiểm tra span `retrieval` để phân tích lý do không tìm thấy tài liệu hoặc lỗi kết nối.
- Mitigation tạm thời: Kiểm tra sức khoẻ của vector store/kho tài liệu; tạm thời kích hoạt prompt fallback sử dụng context cache có sẵn.
- Owner: `student-MaiTienHuy`

