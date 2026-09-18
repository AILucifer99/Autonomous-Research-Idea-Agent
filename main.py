from inference import run_inference

final_state = run_inference(
    topic="Learning and Adaptation in Self-Play Algorithms",
    paper_type="technical",
    target_venue="ieee_conference",
    audience="graph ML researchers",
    depth="deep",
    stream=True,
    create_zip=True,
)

if final_state.get("aborted"):
    print(f"\n[INFO] Workflow halted: {final_state.get('reason', 'User cancelled during pre-flight authorization.')}")
else:
    print(f"\nLaTeX generated at: {final_state.get('output_dir', '')}/main.tex")
    if final_state.get("cost_summary"):
        print(f"Total cost: ${final_state['cost_summary'].get('total_cost_usd', 0.0):.4f} USD")
