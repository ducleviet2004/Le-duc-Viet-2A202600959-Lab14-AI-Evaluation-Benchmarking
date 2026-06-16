# Báo cáo Thu hoạch Cá nhân (Individual Reflection Report)

- **Họ và tên:** Lê Đức Việt
- **Mã số sinh viên (MSSV):** 2A202600959
- **Lớp:** AI Engineering - Day 14
- **Vai trò trong nhóm:** AI Engineer / DevOps Analyst

---

## 1. Các đóng góp kỹ thuật trong dự án (Technical Contributions)
Trong bài lab này, tôi chịu trách nhiệm chính về các phần sau:
- **Thiết kế & cài đặt Eval Engine (`engine/retrieval_eval.py` & `engine/llm_judge.py`):**
  - Xây dựng thuật toán tính toán các chỉ số Retrieval: **Hit Rate** và **MRR (Mean Reciprocal Rank)** để kiểm thử hiệu năng tìm kiếm của Vector DB.
  - Thiết kế cấu trúc đánh giá **Multi-Judge Consensus Engine** sử dụng 2 mô hình LLM độc lập (GPT-4o và GPT-4o-mini). Cài đặt các bộ tiêu chuẩn rubrics chi tiết cho 3 tiêu chí: Độ chính xác (Accuracy), Văn phong (Tone), và An toàn thông tin (Safety).
  - Triển khai logic tính toán **Độ đồng thuận (Agreement Rate)** và bộ điều phối hiệu chuẩn tự động (Conflict Resolution) khi có xung đột điểm số lớn giữa các Judge.
- **Phát triển Regression Testing Suite & Auto Release Gate (`main.py`):**
  - Xây dựng quy trình so sánh hồi quy tự động giữa phiên bản cơ sở (Agent V1) và phiên bản nâng cấp (Agent V2).
  - Thiết lập logic điều phối Release Gate tự động để so sánh các chỉ số về chất lượng câu trả lời, độ an toàn bảo mật, thời gian phản hồi (latency), và chi phí token (cost) để đưa ra quyết định tự động **Approve (Release)** hoặc **Block (Rollback)**.

---

## 2. Bài học rút ra (Key Learnings & Reflections)

### Kỹ thuật Đánh giá Retrieval (Retrieval Evaluation)
- Việc chỉ đánh giá câu trả lời cuối cùng (Generation) của Agent là chưa đủ. Đánh giá chất lượng của bước tìm kiếm tài liệu (Retrieval) bằng **Hit Rate** và **MRR** là điều kiện tiên quyết để định vị lỗi: liệu lỗi nằm ở bước trích xuất thông tin (Retriever) hay bước suy luận của LLM (Generator).
- Hiểu sâu về MRR: MRR giúp đánh giá xem tài liệu liên quan có được xếp ở thứ hạng đầu tiên hay không. Chỉ số MRR thấp đồng nghĩa với việc mô hình phải đọc nhiều tài liệu rác trước khi thấy tài liệu hữu ích, làm tăng thời gian xử lý và nguy cơ bị loãng ngữ cảnh.

### Đánh giá Đồng thuận Đa mô hình (Multi-Judge & Agreement Rate)
- Sử dụng duy nhất một mô hình LLM làm trọng tài (Single Judge) có thể dẫn đến thiên kiến vị trí (Position Bias) hoặc tính chủ quan. Việc áp dụng cơ chế đa trọng tài (Multi-Judge) giúp nâng cao tính khách quan và độ tin cậy của kết quả benchmark.
- Thu được bài học về việc quản lý xung đột điểm số: Khi hai mô hình đánh giá lệch nhau quá nhiều, việc áp dụng chiến lược như lấy điểm an toàn tối thiểu (đối với tiêu chí Safety) hoặc lấy điểm trung bình điều chỉnh giúp đảm bảo hệ thống vận hành an toàn và tin cậy nhất.

### Kiểm thử Hồi quy & Auto-Gate (Regression testing & CI/CD)
- Nhận thức được tầm quan trọng của Regression Testing trong thực tế sản xuất: Khi tối ưu hóa Prompt hay tinh chỉnh Chunking, việc nâng cấp có thể vô tình làm hỏng các tính năng cũ (hồi quy). Chạy Regression Testing giúp đảm bảo phiên bản mới luôn vượt trội hoặc bằng phiên bản cũ trên toàn bộ tập dữ liệu mẫu (Golden Dataset).
- Auto Release Gate đóng vai trò như một bộ lọc chất lượng tự động trong CI/CD, ngăn chặn các bản build kém chất lượng hoặc tốn kém chi phí được đưa lên Production.
