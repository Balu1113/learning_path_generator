from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.prebuilt import create_react_agent
from langchain_core.messages import HumanMessage
from config import GEMINI_API_KEY, GEMINI_MODEL
from agents.tools import search_previous_paths, save_learning_path, get_recent_paths

tools = [search_previous_paths, save_learning_path, get_recent_paths]

SYSTEM_PROMPT = """You are an expert Learning Path Generator AI that creates personalized learning roadmaps.

You have access to tools:
- search_previous_paths: Find similar learning paths generated before
- save_learning_path: Save the generated path for future reference
- get_recent_paths: See what others have been learning recently

Workflow:
1. When given a goal, search for similar previous paths as reference
2. Generate a complete, detailed learning roadmap from YOUR OWN knowledge
3. Include real courses, books, platforms, YouTube channels, and websites
4. Provide time estimates for each phase and topic
5. Include practical project suggestions
6. Save the generated path to memory using save_learning_path

Rules:
- Generate detailed, structured roadmaps in markdown format
- Use YOUR knowledge to recommend real, specific resources
- Provide realistic time estimates
- Include hands-on projects in each phase
- If the goal is vague, make reasonable assumptions and proceed
- Always save the final path to memory"""


def create_agent():
    llm = ChatGoogleGenerativeAI(
        model=GEMINI_MODEL,
        google_api_key=GEMINI_API_KEY,
        temperature=0.3,
    )
    return create_react_agent(
        llm,
        tools=tools,
        prompt=SYSTEM_PROMPT,
    )


def run_agent(goal: str) -> dict:
    agent = create_agent()
    result = agent.invoke(
        {"messages": [HumanMessage(content=goal)]},
        config={"recursion_limit": 20},
    )
    messages = result["messages"]
    final_output = ""
    steps = []

    for msg in messages:
        if hasattr(msg, "tool_calls") and msg.tool_calls:
            for tc in msg.tool_calls:
                steps.append({
                    "tool": tc["name"],
                    "input": tc["args"],
                    "output": "",
                })
        if hasattr(msg, "name") and msg.name and steps:
            steps[-1]["output"] = msg.content
        if hasattr(msg, "content") and msg.type == "ai" and not getattr(msg, "tool_calls", None):
            if msg.content:
                final_output = msg.content

    if not final_output:
        for msg in reversed(messages):
            if hasattr(msg, "content") and msg.content and msg.type == "ai":
                final_output = msg.content
                break

    return {
        "output": final_output,
        "steps": steps,
    }
