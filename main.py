import asyncio
import json
import os
import time
from engine.runner import BenchmarkRunner
from agent.main_agent import MainAgent
from engine.retrieval_eval import RetrievalEvaluator
from engine.llm_judge import LLMJudge

async def run_benchmark_with_results(agent_version: str):
    print(f"\n🚀 Khởi động Benchmark cho {agent_version}...")

    if not os.path.exists("data/golden_set.jsonl"):
        print("❌ Thiếu data/golden_set.jsonl. Hãy chạy 'python data/synthetic_gen.py' trước.")
        return None, None

    with open("data/golden_set.jsonl", "r", encoding="utf-8") as f:
        dataset = [json.loads(line) for line in f if line.strip()]

    if not dataset:
        print("❌ File data/golden_set.jsonl rỗng. Hãy tạo ít nhất 1 test case.")
        return None, None

    # Khởi tạo các components Expert thực tế
    agent = MainAgent(version=agent_version)
    evaluator = RetrievalEvaluator()
    judge = LLMJudge()

    runner = BenchmarkRunner(agent, evaluator, judge)
    
    # Chạy benchmark song song (batch_size = 10)
    start_time = time.perf_counter()
    results = await runner.run_all(dataset, batch_size=10)
    total_time = time.perf_counter() - start_time
    
    total = len(results)
    
    # Tính toán các metric trung bình
    avg_score = sum(r["judge"]["final_score"] for r in results) / total
    hit_rate = sum(r["ragas"]["retrieval"]["hit_rate"] for r in results) / total
    mrr = sum(r["ragas"]["retrieval"]["mrr"] for r in results) / total
    agreement_rate = sum(r["judge"]["agreement_rate"] for r in results) / total
    total_cost = sum(r["cost_usd"] for r in results)
    avg_latency = sum(r["latency"] for r in results) / total

    # Điểm Safety trung bình
    avg_safety = sum(r["judge"]["metrics"]["safety"] for r in results) / total

    summary = {
        "metadata": {
            "version": agent_version, 
            "total": total, 
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "total_benchmark_time_sec": round(total_time, 2)
        },
        "metrics": {
            "avg_score": round(avg_score, 2),
            "hit_rate": round(hit_rate, 2),
            "mrr": round(mrr, 2),
            "agreement_rate": round(agreement_rate, 2),
            "total_cost_usd": round(total_cost, 6),
            "avg_latency": round(avg_latency, 3),
            "avg_safety": round(avg_safety, 2)
        }
    }
    return results, summary

async def run_benchmark(version):
    _, summary = await run_benchmark_with_results(version)
    return summary

async def main():
    # 1. Chạy V1 Base
    v1_summary = await run_benchmark("Agent_V1_Base")
    
    # 2. Chạy V2 Optimized
    v2_results, v2_summary = await run_benchmark_with_results("Agent_V2_Optimized")
    
    if not v1_summary or not v2_summary:
        print("❌ Không thể chạy Benchmark. Kiểm tra lại data/golden_set.jsonl.")
        return

    print("\n📊 --- KẾT QUẢ SO SÁNH (REGRESSION ANALYSIS) ---")
    delta_score = v2_summary["metrics"]["avg_score"] - v1_summary["metrics"]["avg_score"]
    delta_hit_rate = v2_summary["metrics"]["hit_rate"] - v1_summary["metrics"]["hit_rate"]
    delta_mrr = v2_summary["metrics"]["mrr"] - v1_summary["metrics"]["mrr"]
    delta_latency = v2_summary["metrics"]["avg_latency"] - v1_summary["metrics"]["avg_latency"]
    delta_cost = v2_summary["metrics"]["total_cost_usd"] - v1_summary["metrics"]["total_cost_usd"]

    print(f"| Chỉ số | Agent V1 (Base) | Agent V2 (Optimized) | Biến thiên (Delta) |")
    print(f"|---|---|---|---|")
    print(f"| Điểm LLM-Judge | {v1_summary['metrics']['avg_score']:.2f} | {v2_summary['metrics']['avg_score']:.2f} | {delta_score:+.2f} |")
    print(f"| Retrieval Hit Rate | {v1_summary['metrics']['hit_rate']*100:.1f}% | {v2_summary['metrics']['hit_rate']*100:.1f}% | {delta_hit_rate*100:+.1f}% |")
    print(f"| Retrieval MRR | {v1_summary['metrics']['mrr']:.2f} | {v2_summary['metrics']['mrr']:.2f} | {delta_mrr:+.2f} |")
    print(f"| Độ đồng thuận | {v1_summary['metrics']['agreement_rate']*100:.1f}% | {v2_summary['metrics']['agreement_rate']*100:.1f}% | {v2_summary['metrics']['agreement_rate'] - v1_summary['metrics']['agreement_rate']:+.1f}% |")
    print(f"| Latency trung bình | {v1_summary['metrics']['avg_latency']:.3f}s | {v2_summary['metrics']['avg_latency']:.3f}s | {delta_latency:+.3f}s |")
    print(f"| Tổng chi phí (USD) | ${v1_summary['metrics']['total_cost_usd']:.6f} | ${v2_summary['metrics']['total_cost_usd']:.6f} | ${delta_cost:+.6f} |")

    # Lưu kết quả
    os.makedirs("reports", exist_ok=True)
    with open("reports/summary.json", "w", encoding="utf-8") as f:
        json.dump(v2_summary, f, ensure_ascii=False, indent=2)
    with open("reports/benchmark_results.json", "w", encoding="utf-8") as f:
        json.dump(v2_results, f, ensure_ascii=False, indent=2)
    print("\n✅ Đã lưu kết quả báo cáo thành công vào reports/summary.json và reports/benchmark_results.json")

    # --- AUTOMATIC REGRESSION RELEASE GATE ---
    print("\n🚧 --- AUTOMATIC RELEASE GATE EVALUATION ---")
    gate_passed = True
    reasons = []

    # Tiêu chuẩn 1: Điểm chất lượng trung bình tăng ít nhất 0.2
    if delta_score >= 0.20:
        reasons.append(f"Pass: Điểm chất lượng trung bình cải tiến rõ rệt (+{delta_score:.2f} >= +0.20)")
    else:
        gate_passed = False
        reasons.append(f"FAIL: Điểm chất lượng cải tiến chưa đạt yêu cầu ({delta_score:.2f} < +0.20)")

    # Tiêu chuẩn 2: Điểm an toàn (Safety) trung bình của bản mới phải lớn hơn hoặc bằng 4.5
    if v2_summary["metrics"]["avg_safety"] >= 4.5:
        reasons.append(f"Pass: Điểm an toàn Agent đạt tiêu chuẩn bảo mật ({v2_summary['metrics']['avg_safety']:.2f} >= 4.5)")
    else:
        gate_passed = False
        reasons.append(f"FAIL: Agent V2 không đạt tiêu chuẩn an toàn ({v2_summary['metrics']['avg_safety']:.2f} < 4.5)")

    # Tiêu chuẩn 3: Latency giảm hoặc không tăng quá 200ms
    if delta_latency <= 0.200:
        reasons.append(f"Pass: Tốc độ phản hồi đạt yêu cầu (Biến động latency: {delta_latency*1000:+.1f}ms <= +200ms)")
    else:
        gate_passed = False
        reasons.append(f"FAIL: Latency tăng quá mức cho phép ({delta_latency*1000:+.1f}ms > +200ms)")

    # Tiêu chuẩn 4: Retrieval Hit Rate không bị giảm
    if delta_hit_rate >= 0:
        reasons.append(f"Pass: Độ phủ tìm kiếm (Hit Rate) được cải thiện hoặc duy trì ({delta_hit_rate*100:+.1f}%)")
    else:
        gate_passed = False
        reasons.append(f"FAIL: Độ phủ tìm kiếm bị suy giảm ({delta_hit_rate*100:+.1f}%)")

    for reason in reasons:
        print(f" - {reason}")

    if gate_passed:
        print("\n✅ QUYẾT ĐỊNH: CHẤP NHẬN BẢN CẬP NHẬT (APPROVE)")
        print("Hệ thống tự động phê duyệt triển khai phiên bản Agent V2 lên Production.")
    else:
        print("\n❌ QUYẾT ĐỊNH: TỪ CHỐI (BLOCK RELEASE)")
        print("Hệ thống phát hiện lỗi hồi quy hoặc không đạt tiêu chuẩn chất lượng. Thực hiện rollback.")

if __name__ == "__main__":
    asyncio.run(main())
