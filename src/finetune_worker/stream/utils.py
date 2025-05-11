import builtins

# Override print globally
original_print = builtins.print


def custom_print(*args, **kwargs):
    original_print("[stream]", *args, **kwargs)


builtins.print = custom_print
