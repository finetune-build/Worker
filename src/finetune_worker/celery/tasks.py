from finetune_worker.celery.app import celery

@celery.task
def add(x: int, y: int = 10) -> int:
    """
    Adds two numbers together
    """
    return x + y


@celery.task
def multiply(x, y):
    """
    multiplies two numbers together
    """
    return x * y


@celery.task
def subtract(x, y, *args: int, **kwargs):
    """
    subtracts two numbers
    """
    return x - y


@celery.task
def divide(x, y):
    """
    divides two numbers
    """
    return x / y


@celery.task
def divide_all(x, y):
    """
    divides two numbers
    """
    return x / y