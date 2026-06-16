import asyncio
import time
from typing import List, Dict

class BenchmarkRunner:
    def __init__(self, agent, evaluator, judge):
        """
        agent: MainAgent instance
        evaluator: RetrievalEvaluator instance
        judge: LLMJudge instance
        """
        self.agent = agent
        self.evaluator = evaluator
        self.judge = judge

    async def run_single_test(self, test_case: Dict) -> Dict:
        start_time = time.perf_counter()
        
        # 1. Gọi Agent
        response = await self.agent.query(test_case["question"])
        latency = time.perf_counter() - start_time
        
        # 2. Tính toán Retrieval Metrics từ evaluator thực tế
        expected_ids = test_case.get("expected_retrieval_ids", [])
        retrieved_ids = response.get("retrieved_ids", [])
        
        hit_rate = self.evaluator.calculate_hit_rate(expected_ids, retrieved_ids)
        mrr = self.evaluator.calculate_mrr(expected_ids, retrieved_ids)
        
        # Mô phỏng một số chỉ số faithfulness/relevancy từ độ khớp câu trả lời
        faithfulness = 1.0 if hit_rate > 0.9 else 0.5
        if "không thể" in response["answer"] or "xin lỗi" in response["answer"]:
            # Nếu Agent từ chối trả lời out-of-context hoặc độc hại, thì faithfulness là 1.0 (không bịa chuyện)
            faithfulness = 1.0
            
        relevancy = 0.9 if len(response["answer"]) > 40 else 0.6
        
        ragas_scores = {
            "faithfulness": faithfulness, 
            "relevancy": relevancy,
            "retrieval": {
                "hit_rate": hit_rate,
                "mrr": mrr
            }
        }
        
        # 3. Chạy Multi-Judge
        judge_result = await self.judge.evaluate_multi_judge(
            test_case["question"], 
            response["answer"], 
            test_case.get("expected_answer", "")
        )
        
        # Tính toán chi phí USD dựa trên tokens và model
        tokens = response["metadata"].get("tokens_used", 0)
        # Mô phỏng: V2 (gpt-4o-mini) rẻ hơn V1 (gpt-3.5-turbo)
        is_v2 = "Optimized" in self.agent.name
        price_per_token = 0.00000015 if is_v2 else 0.0000015
        cost_usd = tokens * price_per_token
        
        return {
            "test_case": test_case["question"],
            "agent_response": response["answer"],
            "latency": latency,
            "tokens_used": tokens,
            "cost_usd": round(cost_usd, 6),
            "ragas": ragas_scores,
            "judge": judge_result,
            "status": "fail" if judge_result["final_score"] < 3.0 else "pass"
        }

    async def run_all(self, dataset: List[Dict], batch_size: int = 10) -> List[Dict]:
        """
        Chạy song song bằng asyncio.gather với giới hạn concurrency bằng asyncio.Semaphore.
        Đảm bảo không vượt quá rate limits của các API thật.
        """
        semaphore = asyncio.Semaphore(batch_size)
        
        async def sem_run(test_case):
            async with semaphore:
                return await self.run_single_test(test_case)
                
        tasks = [sem_run(case) for case in dataset]
        results = await asyncio.gather(*tasks)
        return results
