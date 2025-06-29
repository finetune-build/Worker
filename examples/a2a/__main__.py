# Extends Hello World Example from a2a-python
import asyncio

from contextlib import asynccontextmanager

from finetune.sse.event_listener import EventListener 

from agent import HelloWorldAgentExecutor
from ftw_request_handler import FTWRequestHandler

from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import (
    AgentCapabilities,
    AgentCard,
    AgentSkill,
)

if __name__ == '__main__':
    skill = AgentSkill(
        id='hello_world',
        name='Returns hello world',
        description='just returns hello world',
        tags=['hello world'],
        examples=['hi', 'hello world'],
    )

    agent_card = AgentCard(
        name='Hello World Agent',
        description='Just a hello world agent',
        url='http://localhost:9998/',
        version='1.0.0',
        defaultInputModes=['text'],
        defaultOutputModes=['text'],
        capabilities=AgentCapabilities(streaming=True),
        skills=[skill],
    )

    # Swaps out `DefaultRequestHandler` with `FTWRequestHandler`.
    request_handler = FTWRequestHandler(
        agent_executor=HelloWorldAgentExecutor(),
        task_store=InMemoryTaskStore(),
    )

    server = A2AStarletteApplication(
        agent_card=agent_card, http_handler=request_handler
    )

    async def persistent_event_listener():
        print("Launching persistent event listener...")
        while True:
            try:
                event_listener = EventListener(request_handler.handle_event)
                await event_listener.start()
            except asyncio.CancelledError:
                print("Event listener task cancelled. Exiting loop.")
                break
            except Exception as e:
                print(f"Event listener crashed with: {e}. Restarting in 1s...")
                await asyncio.sleep(1)

    @asynccontextmanager
    async def lifespan(app):
        print("Starting SSE event listener...")
        task = asyncio.create_task(persistent_event_listener())
        try:
            yield
        finally:
            task.cancel()
            await task


    import uvicorn

    uvicorn.run(server.build(lifespan=lifespan), host='0.0.0.0', port=9998)
