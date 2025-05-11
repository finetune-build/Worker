import importlib
import inspect
from typing import get_type_hints, Any

from celery.app.task import Task

# Import your tasks module
tasks_module = importlib.import_module("finetune_worker.celery.tasks")

# Collect all Celery tasks
celery_tasks = {
    name: obj for name, obj in vars(tasks_module).items() if isinstance(obj, Task)
}


# Get argument info (name, type, default) from a function
def get_task_args_and_kwargs(task_fn):
    sig = inspect.signature(task_fn)
    type_hints = get_type_hints(task_fn)

    arg_info = []
    for name, param in sig.parameters.items():
        arg_type = type_hints.get(name, Any)
        default = param.default if param.default != inspect.Parameter.empty else None
        required = param.default == inspect.Parameter.empty

        arg_info.append(
            {
                "name": name,
                "type": getattr(arg_type, "__name__", str(arg_type)),
                "default": default,
                "required": required,
            }
        )

    return arg_info, type_hints.get("return", None)


# Get docstring of a function
def get_task_docstring(task_fn):
    return task_fn.__doc__


# Print tasks and their metadata
print("📋 Discovered Celery tasks and their metadata:\n")
for name, task in celery_tasks.items():
    args_info, return_type = get_task_args_and_kwargs(task.run)
    docstring = get_task_docstring(task.run)

    print(f"🔧 Tool: {name}")

    if docstring:
        print(f"📘 Description: {docstring.strip()}")

    print("📥 Arguments:")
    for arg in args_info:
        default_display = (
            f"default={repr(arg['default'])}" if not arg["required"] else "required"
        )
        print(f"  - {arg['name']} ({arg['type']}): {default_display}")

    return_display = (
        getattr(return_type, "__name__", str(return_type)) if return_type else "None"
    )
    print(f"📤 Returns: {return_display}")
    print("-" * 60)


# Function to run a task by name
def run_task_by_name(task_name: str, *args, **kwargs):
    task = celery_tasks.get(task_name)
    if task:
        print(f"🚀 Running task: {task_name} with args={args}, kwargs={kwargs}")
        result = task.apply_async(args=args, kwargs=kwargs)
        return result
    else:
        print(f"❌ Task '{task_name}' not found.")
