from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from cbra.engine import initialize_field_state, step_field
from cbra.models import FieldState
import uvicorn

app = FastAPI()

# Global state for the UI demo - Initializing the Field
current_field = initialize_field_state("UI Monitor Active: Exploring Posthumanist Logic")

@app.get("/ui/", response_class=HTMLResponse)
async def get_ui():
    return f"""
    <html>
        <head><title>CBRA v11 Monitor</title></head>
        <body style="font-family: sans-serif; padding: 40px; background-color: #f4f4f9;">
            <h1 style="color: #2c3e50;">CBRA v11 Field Monitor</h1>
            <div style="border: 2px solid #2c3e50; padding: 20px; background: white; border-radius: 8px; max-width: 600px;">
                <p><strong>Field ID:</strong> <code style="background: #eee; padding: 2px 4px;">{current_field.id}</code></p>
                <p><strong>Phenomena:</strong> {current_field.field_signature['phenomena']}</p>
                <hr>
                <p><strong>Care Tension:</strong> <span style="color: {'#e74c3c' if current_field.field_values.care_tension > 0.6 else '#27ae60'};">{current_field.field_values.care_tension:.2f}</span></p>
                <p><strong>Field Coherence:</strong> {current_field.field_values.coherence:.2f}</p>
                <p><strong>Timestep:</strong> {current_field.timestep}</p>
            </div>
            <form action="/ui/step" method="post">
                <button type="submit" style="margin-top: 20px; padding: 12px 24px; background: #3498db; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 16px;">
                    Perform Intra-active Step
                </button>
            </form>
            <p style="font-size: 0.8em; color: #7f8c8d; margin-top: 20px;">Substrate Status: Stable (Python 3.9.6 compatible)</p>
        </body>
    </html>
    """

@app.post("/ui/step")
async def take_step():
    global current_field
    # This calls the stable Intra-action operator we just tested
    step_field(current_field, "UI Manual Step")
    return {
        "status": "Field Stepped", 
        "new_tension": round(current_field.field_values.care_tension, 2),
        "new_coherence": round(current_field.field_values.coherence, 2)
    }

if __name__ == "__main__":
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)
