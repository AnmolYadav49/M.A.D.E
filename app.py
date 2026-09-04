import chainlit as cl
import httpx

# Point this to your local FastAPI server
FASTAPI_URL = "http://127.0.0.1:8000"

@cl.on_chat_start
async def start():
    await cl.Message(
        content="Welcome to the **M.A.D.E. Terminal**. Submit a data task to begin the multi-agent workflow."
    ).send()

@cl.on_message
async def main(message: cl.Message):
    # 1. Create a dynamic loading step to show the agents working
    async with cl.Step(name="Agentic Orchestrator") as step:
        step.output = "Triggering LangGraph workflow on backend..."
        
        # 2. Ping the FastAPI /execute-task endpoint
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{FASTAPI_URL}/execute-task",
                    json={"task": message.content},
                    timeout=60.0
                )
                response.raise_for_status()
                data = response.json()
                
                step.output = "Agents finished. Awaiting Human-in-the-Loop approval."
                step.status = "success"
            except Exception as e:
                step.output = f"API Error: {str(e)}"
                step.status = "error"
                return

    # 3. Safely Extract and Render the Data
    try:
        report = data.get("reviewer_security_report", "No report generated.")
        code = data.get("proposed_code", "# No code generated.")
        
        # Save the code in the user's session state so the button can access it later
        cl.user_session.set("proposed_code", code)

        # 4. Format the output markdown
        content = f"### 🛡️ Reviewer Security Report\n{report}\n\n### 💻 Proposed Code\n```python\n{code}\n```"

        # 5. Inject the dynamic HITL (Human-in-the-Loop) Buttons
        actions = [
            cl.Action(name="approve_code", payload={"action": "approve"}, label="✅ Approve & Run"),
            cl.Action(name="reject_code", payload={"action": "reject"}, label="❌ Reject")
        ]

        await cl.Message(content=content, actions=actions).send()
        
    except Exception as e:
        # If the UI crashes, it will now print exactly why on the screen
        await cl.Message(content=f"⚠️ **Frontend Rendering Error:** `{str(e)}`\n\nCheck the Chainlit terminal for the full traceback.").send()