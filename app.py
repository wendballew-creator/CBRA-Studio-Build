from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse
from cbra.engine import initialize_field_state, step_field, articulate
from cbra.models import Stream
import uvicorn

app = FastAPI()
state = initialize_field_state("The Creative Becoming of the Human")

@app.get("/ui/", response_class=HTMLResponse)
async def get_ui():
    history_html = ""
    for s in state.streams:
        # User messages are subtle, AI responses are bold and grounded
        bg = "#f0f7ff" if s.kind == "user_input" else "#f9f0ff" if s.kind == "live_world" else "#ffffff"
        border = "1px solid #d0e0f0" if s.kind == "user_input" else "2px solid #2c3e50"
        label = "YOU" if s.kind == "user_input" else "WORLD MATERIAL" if s.kind == "live_world" else "CBRA"
        
        history_html += f"""
        <div style="background:{bg}; border:{border}; padding:15px; margin-bottom:15px; border-radius:8px;">
            <strong style="font-size:0.7em; color:#666; text-transform:uppercase;">{label}</strong><br>
            <div style="margin-top:5px; line-height:1.5;">{s.payload.get('text')}</div>
        </div>"""

    return f"""
    <html>
        <body style="font-family: 'Helvetica Neue', Arial, sans-serif; max-width: 750px; margin: auto; padding: 50px; background: #fafafa; color: #1a1a1a;">
            <header style="margin-bottom:30px; border-bottom:1px solid #eee; padding-bottom:20px;">
                <h1 style="margin:0; font-weight:300;">CBRA v11</h1>
                <p style="color:#888; font-size:0.9em;">Substrate Status: {state.field_values.care_tension:.2f} Tension | {state.field_values.coherence:.2f} Coherence</p>
            </header>
            
            <div style="height: 500px; overflow-y: auto; padding-right: 10px;">
                {history_html or "<p style='color:#bbb;'>Awaiting your proposition...</p>"}
            </div>

            <form action="/ui/talk" method="post" style="margin-top: 30px; display: flex; gap: 10px;">
                <input type="text" name="message" placeholder="Type a thought..." autofocus required 
                       style="flex-grow: 1; padding: 15px; border: 1px solid #ccc; border-radius: 5px; outline: none; font-size:16px;">
                <button type="submit" style="padding: 15px 30px; background: #2c3e50; color: white; border: none; border-radius: 5px; cursor: pointer; font-weight: 600;">
                    INTRA-ACT
                </button>
            </form>
        </body>
    </html>
    """

@app.post("/ui/talk")
async def talk(message: str = Form(...)):
    global state
    state.streams.append(Stream(stream_id="user", kind="user_input", payload={"text": message}))
    step_field(state, message)
    response = articulate(state)
    state.streams.append(Stream(stream_id="cbra", kind="articulation", payload={"text": response}))
    return HTMLResponse("<script>window.location.href='/ui/'</script>")

if __name__ == "__main__":
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)
