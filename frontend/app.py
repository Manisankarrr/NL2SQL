# Gradio version: 5.29.1
# Compatibility notes:
#   - theme and css passed to gr.Blocks() not launch()
#   - Chatbot uses tuple format history [(user, bot), ...]
#   - bubble_full_width removed (not in 5.x)
#   - render_markdown replaced with sanitize_html=False
#   - Example buttons use lambda with default arg to avoid closure bug

import gradio as gr
import requests
import pandas as pd
import os
from datetime import datetime
from pathlib import Path

BASE_URL = os.environ.get("BACKEND_URL", "http://localhost:8000")
CSS_PATH = Path(__file__).parent / "static" / "style.css"


def load_css() -> str:
    return CSS_PATH.read_text(encoding="utf-8") if CSS_PATH.exists() else ""


def get_health() -> dict:
    try:
        r = requests.get(f"{BASE_URL}/api/health", timeout=3)
        return r.json()
    except Exception:
        return {
            "status": "offline",
            "openrouter": False,
            "groq": False,
            "active_provider": "unknown",
            "active_model": "unknown",
        }


def chat(user_message: str, history: list, session_data: dict) -> tuple:
    """Main chat handler. Returns (updated_history, session_data)"""
    if not user_message.strip():
        return history, session_data

    try:
        response = requests.post(
            f"{BASE_URL}/api/query",
            json={"user_input": user_message},
            timeout=30,
        )
        data = response.json()
    except requests.exceptions.ConnectionError:
        error_html = (
            "<div class='bot-error'>⚠️ Cannot connect to backend. "
            "Run: <code>uvicorn backend.main:app --reload</code></div>"
        )
        history.append((user_message, error_html))
        return history, session_data
    except Exception as e:
        history.append((user_message, f"<div class='bot-error'>Error: {str(e)}</div>"))
        return history, session_data

    # ── Intent badge colour map ──
    intent = data.get("intent", "")
    intent_colors = {
        "SELECT": "#3b82f6",
        "INSERT": "#10b981",
        "UPDATE": "#f59e0b",
        "DELETE": "#ef4444",
        "UNKNOWN": "#94a3b8",
    }
    color = intent_colors.get(intent, "#94a3b8")

    # ── Build rich HTML bot bubble ──
    response_html = "<div class='bot-message'>"

    # Header row: intent badge · provider · timing
    response_html += "<div style='display:flex;align-items:center;gap:8px;margin-bottom:10px;flex-wrap:wrap'>"
    response_html += (
        f"<span style='background:{color};color:white;padding:2px 10px;"
        f"border-radius:20px;font-size:11px;font-weight:700;letter-spacing:0.05em'>{intent}</span>"
    )
    if data.get("provider"):
        response_html += (
            f"<span style='color:#94a3b8;font-size:12px'>🤖 {data['provider']}</span>"
        )
    if data.get("execution_time_ms"):
        response_html += (
            f"<span style='color:#94a3b8;font-size:12px'>⚡ {data['execution_time_ms']}ms</span>"
        )
    if data.get("error"):
        response_html += (
            "<span style='background:rgba(239,68,68,0.12);color:#ef4444;"
            "padding:2px 10px;border-radius:20px;font-size:11px;font-weight:700'>ERROR</span>"
        )
    response_html += "</div>"

    # Main message text
    response_html += (
        f"<p style='margin:0 0 12px;font-size:15px;line-height:1.6;color:#0f172a'>"
        f"{data['message']}</p>"
    )

    # Results table
    table_data = data.get("table", [])
    columns = data.get("columns", [])
    if table_data and columns:
        response_html += (
            "<div style='overflow-x:auto;margin:12px 0;border:1px solid #e2e8f0;"
            "border-radius:8px;overflow:hidden'>"
            "<table style='width:100%;border-collapse:collapse;font-size:13px'>"
            "<thead><tr>"
        )
        for col in columns:
            response_html += (
                f"<th style='background:#f1f5f9;padding:8px 12px;text-align:left;"
                f"font-size:11px;text-transform:uppercase;letter-spacing:0.05em;"
                f"color:#64748b;border-bottom:2px solid #e2e8f0;white-space:nowrap'>{col}</th>"
            )
        response_html += "</tr></thead><tbody>"
        for i, row in enumerate(table_data):
            bg = "#ffffff" if i % 2 == 0 else "#f8fafc"
            response_html += f"<tr style='background:{bg}'>"
            for col in columns:
                val = row.get(col, "") if isinstance(row, dict) else ""
                response_html += (
                    f"<td style='padding:8px 12px;border-bottom:1px solid #e2e8f0;"
                    f"color:#0f172a'>{val}</td>"
                )
            response_html += "</tr>"
        response_html += "</tbody></table></div>"
        count = data.get("count", len(table_data))
        response_html += (
            f"<p style='font-size:12px;color:#94a3b8;margin:4px 0 12px'>"
            f"{count} row{'s' if count != 1 else ''} returned</p>"
        )

    # SQL accordion
    if data.get("sql_used"):
        sql_escaped = data["sql_used"].replace("<", "&lt;").replace(">", "&gt;")
        response_html += (
            f"<details style='margin-top:8px;background:#0f172a;border-radius:8px;overflow:hidden'>"
            f"<summary style='cursor:pointer;font-size:13px;color:#818cf8;font-weight:500;"
            f"padding:10px 14px;list-style:none;user-select:none'>▶ View generated SQL</summary>"
            f"<pre style='background:#0f172a;color:#e2e8f0;padding:14px 16px;"
            f"font-size:12px;overflow-x:auto;margin:0;line-height:1.7;"
            f"font-family:monospace'>{sql_escaped}</pre>"
            f"</details>"
        )

    response_html += "</div>"

    history.append((user_message, response_html))

    # Update session history log
    if "history_log" not in session_data:
        session_data["history_log"] = []
    session_data["history_log"].append(
        {
            "time": datetime.now().strftime("%H:%M:%S"),
            "query": user_message,
            "intent": intent,
            "sql": data.get("sql_used", ""),
            "rows": data.get("count", 0),
            "ms": data.get("execution_time_ms", 0),
            "error": data.get("error", False),
        }
    )

    return history, session_data


def build_status_html() -> str:
    health = get_health()
    ok = health.get("status") != "offline"
    dot = "🟢" if ok else "🔴"
    provider = health.get("active_provider", "unknown")
    model = health.get("active_model", "unknown")
    model_short = model.split("/")[-1] if "/" in model else model

    return (
        f"<div style='padding:12px 0'>"
        f"<div style='display:flex;align-items:center;gap:8px;margin-bottom:6px'>"
        f"<span style='font-size:16px'>{dot}</span>"
        f"<span style='color:#f8fafc;font-weight:600;font-size:14px'>"
        f"{'Connected' if ok else 'Offline'}</span>"
        f"</div>"
        f"<div style='font-size:12px;color:#64748b;line-height:1.8'>"
        f"Provider: <span style='color:#94a3b8'>{provider}</span><br>"
        f"Model: <span style='color:#94a3b8'>{model_short}</span>"
        f"</div>"
        f"</div>"
    )


EXAMPLE_QUERIES = [
    "Show all appointments for today",
    "Add appointment for Rahul tomorrow at 5 PM",
    "Show all scheduled appointments",
    "Cancel Ravi's appointment",
    "Update Priya appointment to 6 PM tomorrow",
    "How many appointments this week?",
    "Show completed appointments",
    "List all barbers",
]


def build_analytics_html(session: dict) -> str:
    log = session.get("history_log", [])
    if not log:
        return """
        <div style='text-align:center;padding:40px;color:#94a3b8;font-size:16px;'>
          📊 No queries yet — start chatting to see analytics!
        </div>
        """
    total_queries = len(log)
    
    # Most common intent
    intents = [h.get("intent", "UNKNOWN") for h in log]
    if intents:
        from collections import Counter
        most_common_intent = Counter(intents).most_common(1)[0][0]
    else:
        most_common_intent = "N/A"
        
    # Avg response time
    ms_list = [h.get("ms", 0.0) for h in log]
    avg_ms = round(sum(ms_list) / len(ms_list), 2) if ms_list else 0.0
    
    # Total rows fetched
    total_rows = sum([h.get("rows", 0) for h in log])
    
    return f"""
    <div style='display:grid;grid-template-columns:repeat(4,1fr);gap:16px;margin-bottom:24px'>
      <div style='background:#ffffff;border:1px solid #e2e8f0;border-radius:12px;padding:20px;box-shadow:0 1px 3px rgba(0,0,0,0.05)'>
        <div style='color:#64748b;font-size:12px;font-weight:600;text-transform:uppercase;letter-spacing:0.05em;margin-bottom:4px'>Total Queries</div>
        <div style='color:#0f172a;font-size:28px;font-weight:700'>{total_queries}</div>
      </div>
      <div style='background:#ffffff;border:1px solid #e2e8f0;border-radius:12px;padding:20px;box-shadow:0 1px 3px rgba(0,0,0,0.05)'>
        <div style='color:#64748b;font-size:12px;font-weight:600;text-transform:uppercase;letter-spacing:0.05em;margin-bottom:4px'>Common Intent</div>
        <div style='color:#0f172a;font-size:28px;font-weight:700'>{most_common_intent}</div>
      </div>
      <div style='background:#ffffff;border:1px solid #e2e8f0;border-radius:12px;padding:20px;box-shadow:0 1px 3px rgba(0,0,0,0.05)'>
        <div style='color:#64748b;font-size:12px;font-weight:600;text-transform:uppercase;letter-spacing:0.05em;margin-bottom:4px'>Avg Response Time</div>
        <div style='color:#0f172a;font-size:28px;font-weight:700'>{avg_ms} ms</div>
      </div>
      <div style='background:#ffffff;border:1px solid #e2e8f0;border-radius:12px;padding:20px;box-shadow:0 1px 3px rgba(0,0,0,0.05)'>
        <div style='color:#64748b;font-size:12px;font-weight:600;text-transform:uppercase;letter-spacing:0.05em;margin-bottom:4px'>Total Rows Fetched</div>
        <div style='color:#0f172a;font-size:28px;font-weight:700'>{total_rows}</div>
      </div>
    </div>
    """


def get_intent_data(session: dict) -> list[dict]:
    log = session.get("history_log", [])
    if not log:
        return []
    from collections import Counter
    intents = [h.get("intent", "UNKNOWN") for h in log]
    counts = Counter(intents)
    return [{"intent": intent, "count": count} for intent, count in counts.items()]


def get_timing_data(session: dict) -> list[dict]:
    log = session.get("history_log", [])
    if not log:
        return []
    return [{"query_number": i + 1, "ms": h.get("ms", 0.0)} for i, h in enumerate(log)]


# ── Build the app ──────────────────────────────────────────────────────────────

with gr.Blocks(
    css=load_css(),
    title="BarberSQL",
    theme=gr.themes.Base(
        primary_hue="indigo",
        secondary_hue="slate",
        neutral_hue="slate",
        font=gr.themes.GoogleFont("Inter"),
        font_mono=gr.themes.GoogleFont("JetBrains Mono"),
    ),
) as demo:

    session_state = gr.State({})
    example_btns = []

    with gr.Row(equal_height=True):

        # ── SIDEBAR ──────────────────────────────────────────────────────────
        with gr.Column(scale=0, min_width=280, elem_id="sidebar-col"):

            gr.HTML("""
                <div style='padding-bottom:24px;border-bottom:1px solid rgba(255,255,255,0.08);margin-bottom:24px'>
                  <div style='display:flex;align-items:center;gap:10px;margin-bottom:4px'>
                    <span style='font-size:24px'>✂️</span>
                    <span style='color:#f8fafc;font-size:20px;font-weight:700;letter-spacing:-0.02em'>
                      BarberSQL
                    </span>
                  </div>
                  <div style='color:#475569;font-size:13px'>Natural language → SQL</div>
                </div>
            """)

            status_html = gr.HTML(build_status_html())

            refresh_status_btn = gr.Button(
                "↻ Refresh Status",
                size="sm",
                variant="secondary",
                elem_classes=["example-btn"],
            )

            gr.HTML(
                "<div style='color:#475569;font-size:11px;font-weight:700;"
                "text-transform:uppercase;letter-spacing:0.08em;margin:20px 0 10px'>"
                "Example Queries</div>"
            )

            for query in EXAMPLE_QUERIES:
                btn = gr.Button(
                    query,
                    elem_classes=["example-btn"],
                    size="sm",
                )
                example_btns.append((btn, query))

            gr.HTML("""
                <div style='padding-top:24px;border-top:1px solid rgba(255,255,255,0.08);margin-top:32px'>
                  <div style='color:#334155;font-size:12px;line-height:1.8'>
                    Powered by OpenRouter + Groq<br>
                    MySQL · FastAPI · Gradio
                  </div>
                </div>
            """)

        # ── MAIN AREA ─────────────────────────────────────────────────────────
        with gr.Column(scale=1):

            gr.HTML("""
                <div style='padding:24px 32px 0'>
                  <h1 style='font-size:24px;font-weight:700;color:#0f172a;margin:0 0 4px;
                             letter-spacing:-0.02em'>Appointment Assistant</h1>
                  <p style='color:#64748b;font-size:14px;margin:0'>
                    Ask anything about your barber shop appointments in plain English
                  </p>
                </div>
            """)

            with gr.Tabs():

                # Chat tab
                with gr.Tab("💬 Chat"):
                    chatbot = gr.Chatbot(
                        label="",
                        height=520,
                        show_label=False,
                        elem_id="main-chatbot",
                        sanitize_html=False,
                        type="tuples"
                    )

                    with gr.Row():
                        msg_input = gr.Textbox(
                            placeholder="Ask about appointments… e.g. 'Show today's appointments'",
                            show_label=False,
                            scale=9,
                            elem_id="msg-input",
                            lines=1,
                        )
                        send_btn = gr.Button(
                            "Send ➤",
                            variant="primary",
                            scale=1,
                            min_width=90,
                            elem_id="send-btn",
                        )

                    gr.HTML(
                        "<div style='text-align:center;padding:8px 0;color:#94a3b8;font-size:12px'>"
                        "Press Enter to send</div>"
                    )

                # History tab
                with gr.Tab("📋 History"):
                    history_display = gr.Dataframe(
                        headers=["Time", "Query", "Intent", "Rows", "ms", "Error"],
                        label="Query history this session",
                        interactive=False,
                        wrap=True,
                    )
                    refresh_history_btn = gr.Button(
                        "↻ Refresh", size="sm", variant="secondary"
                    )

                # Analytics tab
                with gr.Tab("📊 Analytics"):
                    analytics_html = gr.HTML(build_analytics_html({}))
                    
                    with gr.Row():
                        intent_plot = gr.BarPlot(
                            value=None,
                            x="intent",
                            y="count",
                            title="Queries by intent",
                            color="intent",
                            color_map={"SELECT": "#3b82f6", "INSERT": "#10b981", "UPDATE": "#f59e0b", "DELETE": "#ef4444"},
                            tooltip=["intent", "count"],
                            height=250
                        )
                        timing_plot = gr.LinePlot(
                            value=None,
                            x="query_number",
                            y="ms",
                            title="Response time per query (ms)",
                            tooltip=["query_number", "ms"],
                            height=250
                        )
                        
                    refresh_analytics_btn = gr.Button(
                        "↻ Refresh Analytics", size="sm", variant="secondary"
                    )

                # About tab
                with gr.Tab("ℹ️ About"):
                    gr.HTML("""
                        <div style='padding:24px;max-width:640px'>
                          <h2 style='font-size:18px;font-weight:700;margin-bottom:20px;
                                     color:#0f172a'>How it works</h2>
                          <div style='display:flex;flex-direction:column;gap:16px'>

                            <div style='display:flex;gap:14px;align-items:flex-start'>
                              <span style='background:#eef2ff;color:#6366f1;width:28px;height:28px;
                                           border-radius:50%;display:flex;align-items:center;
                                           justify-content:center;font-weight:700;font-size:13px;
                                           flex-shrink:0'>1</span>
                              <div>
                                <strong style='font-size:14px;color:#0f172a'>Intent classification</strong>
                                <p style='color:#64748b;font-size:13px;margin:3px 0 0;line-height:1.6'>
                                  Detects whether you want to SELECT, INSERT, UPDATE, or DELETE
                                </p>
                              </div>
                            </div>

                            <div style='display:flex;gap:14px;align-items:flex-start'>
                              <span style='background:#eef2ff;color:#6366f1;width:28px;height:28px;
                                           border-radius:50%;display:flex;align-items:center;
                                           justify-content:center;font-weight:700;font-size:13px;
                                           flex-shrink:0'>2</span>
                              <div>
                                <strong style='font-size:14px;color:#0f172a'>Entity extraction</strong>
                                <p style='color:#64748b;font-size:13px;margin:3px 0 0;line-height:1.6'>
                                  Pulls out names, dates, and times from your natural language
                                </p>
                              </div>
                            </div>

                            <div style='display:flex;gap:14px;align-items:flex-start'>
                              <span style='background:#eef2ff;color:#6366f1;width:28px;height:28px;
                                           border-radius:50%;display:flex;align-items:center;
                                           justify-content:center;font-weight:700;font-size:13px;
                                           flex-shrink:0'>3</span>
                              <div>
                                <strong style='font-size:14px;color:#0f172a'>SQL generation</strong>
                                <p style='color:#64748b;font-size:13px;margin:3px 0 0;line-height:1.6'>
                                  Schema-aware prompt sent to LLM via OpenRouter or Groq
                                </p>
                              </div>
                            </div>

                            <div style='display:flex;gap:14px;align-items:flex-start'>
                              <span style='background:#eef2ff;color:#6366f1;width:28px;height:28px;
                                           border-radius:50%;display:flex;align-items:center;
                                           justify-content:center;font-weight:700;font-size:13px;
                                           flex-shrink:0'>4</span>
                              <div>
                                <strong style='font-size:14px;color:#0f172a'>Safety validation</strong>
                                <p style='color:#64748b;font-size:13px;margin:3px 0 0;line-height:1.6'>
                                  Blocks DROP, TRUNCATE, ALTER and unguarded DELETE/UPDATE
                                </p>
                              </div>
                            </div>

                            <div style='display:flex;gap:14px;align-items:flex-start'>
                              <span style='background:#eef2ff;color:#6366f1;width:28px;height:28px;
                                           border-radius:50%;display:flex;align-items:center;
                                           justify-content:center;font-weight:700;font-size:13px;
                                           flex-shrink:0'>5</span>
                              <div>
                                <strong style='font-size:14px;color:#0f172a'>Execution + response</strong>
                                <p style='color:#64748b;font-size:13px;margin:3px 0 0;line-height:1.6'>
                                  Safe MySQL execution with results formatted in plain English
                                </p>
                              </div>
                            </div>

                          </div>
                        </div>
                    """)

    # ── Event handlers ─────────────────────────────────────────────────────────

    def handle_chat(message: str, history: list, session: dict) -> tuple:
        history, session = chat(message, history, session)
        return "", history, session

    def refresh_history(session: dict) -> list:
        log = session.get("history_log", [])
        if not log:
            return []
        return [
            [h["time"], h["query"], h["intent"], h["rows"], h["ms"], h["error"]]
            for h in log
        ]

    # Send on Enter key or button click
    msg_input.submit(
        handle_chat,
        inputs=[msg_input, chatbot, session_state],
        outputs=[msg_input, chatbot, session_state],
    )
    send_btn.click(
        handle_chat,
        inputs=[msg_input, chatbot, session_state],
        outputs=[msg_input, chatbot, session_state],
    )

    # Wire example buttons — each fills msg_input with its query
    for btn, query in example_btns:
        btn.click(
            fn=lambda q=query: q,
            inputs=None,
            outputs=msg_input,
        )

    # Refresh status panel
    refresh_status_btn.click(fn=build_status_html, inputs=[], outputs=[status_html])

    # Refresh history tab
    refresh_history_btn.click(
        fn=refresh_history,
        inputs=[session_state],
        outputs=[history_display],
    )

    # Analytics event wiring
    def refresh_analytics(session: dict):
        html = build_analytics_html(session)
        
        intent_list = get_intent_data(session)
        df_intent = pd.DataFrame(intent_list) if intent_list else pd.DataFrame(columns=["intent", "count"])
        
        timing_list = get_timing_data(session)
        df_timing = pd.DataFrame(timing_list) if timing_list else pd.DataFrame(columns=["query_number", "ms"])
        
        return html, df_intent, df_timing

    refresh_analytics_btn.click(
        fn=refresh_analytics,
        inputs=[session_state],
        outputs=[analytics_html, intent_plot, timing_plot],
    )


if __name__ == "__main__":
    demo.launch(
        server_name="127.0.0.1",
        server_port=7860,
        share=False,
        show_error=True
    )
