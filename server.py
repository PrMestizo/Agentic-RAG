from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import json
import asyncio
from graph import graph
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

app = FastAPI(title="Agentic RAG Chatbot Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve index.html at root
@app.get("/")
async def get_index():
    import os
    if not os.path.exists("static/index.html"):
        return {"status": "Frontend not created yet. Please create static/index.html"}
    return FileResponse("static/index.html")

# Chat stream endpoint
@app.post("/api/chat")
async def chat_endpoint(request: Request):
    data = await request.json()
    messages = data.get("messages", [])
    
    # Format messages for LangGraph
    langchain_messages = []
    for msg in messages:
        role = msg.get("role")
        content = msg.get("content")
        if role == "user":
            langchain_messages.append(HumanMessage(content=content))
        elif role == "assistant":
            langchain_messages.append(AIMessage(content=content))
        elif role == "system":
            langchain_messages.append(SystemMessage(content=content))
            
    async def event_generator():
        try:
            inputs = {"messages": langchain_messages}
            # Stream events using graph.astream_events
            async for event in graph.astream_events(inputs, version="v2"):
                event_type = event["event"]
                name = event["name"]
                
                # Yield when entering a node
                if event_type == "on_chain_start" and name in ["generate_query_or_respond", "retrieve", "rewrite_question", "generate_answer"]:
                    yield f"data: {json.dumps({'type': 'status', 'status': 'start', 'node': name})}\n\n"
                    
                # Yield when leaving a node
                elif event_type == "on_chain_end" and name in ["generate_query_or_respond", "retrieve", "rewrite_question", "generate_answer"]:
                    yield f"data: {json.dumps({'type': 'status', 'status': 'end', 'node': name})}\n\n"
                    
                # Parse and yield retrieved document sources
                elif event_type == "on_tool_end" and name == "retrieve_documents":
                    output = event["data"]["output"]
                    if hasattr(output, "content"):
                        output_text = output.content
                    elif isinstance(output, dict) and "content" in output:
                        output_text = output["content"]
                    else:
                        output_text = str(output)
                    import re
                    # Split string by the Document header format to isolate individual documents and their metadata
                    parts = re.split(r'Document (\d+) \(Source: ([^)]+)\):\r?\n', output_text)
                    sources = []
                    for idx in range(1, len(parts), 3):
                        if idx + 2 < len(parts):
                            doc_num = parts[idx].strip()
                            source_file = parts[idx+1].strip()
                            text_content = parts[idx+2].strip()
                            # Strip the prepended RAG metadata context header to get the clean source text snippet
                            if "Original Text:" in text_content:
                                text_content = text_content.split("Original Text:", 1)[1].strip()
                            sources.append({
                                "index": doc_num,
                                "source": source_file,
                                "content": text_content
                            })
                    if sources:
                        yield f"data: {json.dumps({'type': 'sources', 'sources': sources})}\n\n"
                    
                # Yield LLM tokens
                elif event_type == "on_chat_model_stream":
                    chunk = event["data"]["chunk"]
                    if chunk and hasattr(chunk, "content") and chunk.content:
                        yield f"data: {json.dumps({'type': 'token', 'token': chunk.content})}\n\n"
                        
        except Exception as e:
            print(f"Error streaming events: {e}")
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
            
    return StreamingResponse(event_generator(), media_type="text/event-stream")

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)
