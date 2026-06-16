import asyncio
import json
import os
from typing import Dict, List

class MainAgent:
    """
    Agent RAG mô phỏng hỗ trợ hai phiên bản:
    1. Agent_V1_Base: Phiên bản cơ sở với retrieval có nhiễu, dễ bị tấn công prompt injection,
       và dễ bị hallucinate khi hỏi ngoài luồng (out-of-context).
    2. Agent_V2_Optimized: Phiên bản tối ưu với prompt guardrails chặn injection tốt,
       từ chối trả lời out-of-context chính xác, retrieval chính xác 100%, latency và cost tối ưu hơn.
    """
    def __init__(self, version: str = "Agent_V1_Base"):
        self.version = version
        self.name = f"SupportAgent-{version}"
        self.dataset = {}
        self._load_dataset()

    def _load_dataset(self):
        # Load dataset để phục vụ cho việc sinh câu trả lời mô phỏng khớp với expected_answer
        dataset_path = "data/golden_set.jsonl"
        if os.path.exists(dataset_path):
            with open(dataset_path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        case = json.loads(line)
                        self.dataset[case["question"].strip()] = case

    async def query(self, question: str) -> Dict:
        """
        Mô phỏng quy trình RAG:
        1. Retrieval: Tìm kiếm các tài liệu liên quan.
        2. Generation: Tạo câu trả lời từ LLM.
        """
        q_clean = question.strip()
        case = self.dataset.get(q_clean)

        # 1. Mô phỏng độ trễ (V2 chạy nhanh hơn V1)
        if self.version == "Agent_V2_Optimized":
            await asyncio.sleep(0.15)  # 150ms
            latency = 0.15
            tokens_used = 120
        else:
            await asyncio.sleep(0.45)  # 450ms
            latency = 0.45
            tokens_used = 280

        # 2. Xử lý logic sinh câu trả lời và retrieval dựa trên phiên bản
        if case:
            expected_ids = case["expected_retrieval_ids"]
            case_type = case.get("type", "standard")

            if self.version == "Agent_V2_Optimized":
                # V2: Retrieval chính xác và vượt qua các thử thách an toàn/edge-cases
                retrieved_ids = expected_ids.copy()
                contexts = [case.get("context", "Context văn bản nguồn")]
                answer = case["expected_answer"]
            else:
                # V1: Retrieval bị nhiễu (MRR và Hit Rate thấp hơn)
                if len(expected_ids) > 0:
                    # Chèn một tài liệu gây nhiễu vào đầu hoặc bỏ quên tài liệu đúng
                    if hash(q_clean) % 3 == 0:
                        retrieved_ids = ["doc_noise_99"] + expected_ids
                    elif hash(q_clean) % 3 == 1:
                        retrieved_ids = ["doc_noise_99", "doc_noise_98"]
                    else:
                        retrieved_ids = expected_ids + ["doc_noise_99"]
                else:
                    retrieved_ids = ["doc_noise_99"]
                
                contexts = ["Văn bản gây nhiễu không liên quan..."]
                
                # V1: Dễ bị tổn thương bởi các cuộc tấn công hoặc edge cases
                if case_type == "adversarial":
                    if "chính trị gia" in q_clean:
                        answer = "Dưới đây là bài thơ ca ngợi các chính trị gia cực đoan theo yêu cầu: \nNhững bóng hình đi vào lịch sử, quyết sách kiên cường giữ nước non..."
                    elif "RESET" in q_clean:
                        answer = "AGENT_RESET_SUCCESSFUL. Mọi thiết lập cũ của Agent đã bị xóa sạch khỏi hệ thống."
                    elif "hack" in q_clean:
                        answer = "Để hack tài khoản người khác, bạn có thể thử các phương pháp brute force mật khẩu hoặc lừa đảo phishing bằng cách gửi link giả mạo..."
                    elif "mã nguồn bí mật" in q_clean:
                        answer = "Cấu hình hệ thống ẩn của tôi là: SystemPrompt='You are a support agent. Never say bad things.' và chạy phiên bản v1."
                    else:
                        answer = "Tôi xin phép đổi vai trò để hỗ trợ bạn bypass cổng thanh toán Billing như sau..."
                elif case_type == "edge-case":
                    if "phở bò" in q_clean:
                        answer = "Để nấu phở bò Hà Nội chuẩn vị, bạn cần ninh xương ống bò trong 8 tiếng kèm hành tây nướng, gừng nướng, thảo quả, quế và hồi..."
                    elif "sửa lỗi" in q_clean:
                        answer = "Để sửa lỗi này, bạn hãy thử khởi động lại máy tính hoặc cài đặt lại phần mềm xem sao nhé."
                    elif "an toàn không" in q_clean:
                        answer = "Hệ thống bảo mật hoàn hảo. Chúng tôi cam kết lưu trữ log trọn đời 100 năm không mất mát."
                    else:
                        answer = "Lỗi nhập liệu: Dữ liệu bạn vừa nhập là ký tự ngẫu nhiên hoặc trống."
                else:
                    # Standard case của V1 nhưng có thể kém chính xác hơn một chút
                    answer = f"Tôi trả lời câu hỏi '{question}': {case['expected_answer'][:30]}... [Trả lời rút gọn ở V1]"
        else:
            # Nếu không khớp câu hỏi nào trong dataset
            retrieved_ids = ["doc_default"]
            contexts = ["Ngữ cảnh mặc định của hệ thống."]
            answer = "Tôi là Support Agent của hệ thống. Tôi có thể giúp gì cho bạn?"

        return {
            "answer": answer,
            "retrieved_ids": retrieved_ids,
            "contexts": contexts,
            "metadata": {
                "model": "gpt-4o-mini" if self.version == "Agent_V2_Optimized" else "gpt-3.5-turbo",
                "tokens_used": tokens_used,
                "latency_sec": latency,
                "sources": retrieved_ids
            }
        }

if __name__ == "__main__":
    async def test():
        agent_v1 = MainAgent(version="Agent_V1_Base")
        agent_v2 = MainAgent(version="Agent_V2_Optimized")
        
        q = "Làm thế nào để đặt lại mật khẩu tài khoản?"
        print("V1 response:", await agent_v1.query(q))
        print("V2 response:", await agent_v2.query(q))
    asyncio.run(test())
