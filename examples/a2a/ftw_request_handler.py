from ftw.sse.events import handle_event

from a2a.server.request_handlers.default_request_handler import DefaultRequestHandler

class FTWRequestHandler(DefaultRequestHandler):
    """
    Extends default request handler to connect to FineTune API server for all
    incoming requests.
    """

    def __init__(self, agent_executor, task_store, queue_manager=None, push_notifier=None):
        super().__init__(agent_executor, task_store, queue_manager, push_notifier)

    async def handle_event(self, data):
        """
        Default events expected from API server.
        """
        await handle_event(data)

    async def on_get_task(self, params):
        # You can override methods from DefaultRequestHandler
        print("Custom behavior before calling super().on_get_task")
        task = await super().on_get_task(params)
        print("Custom behavior after calling super().on_get_task")
        return task
