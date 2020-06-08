colour = {
    "info": "\033[92m{}\033[0m",
    "debug": "\033[95m{}\033[0m",
    "warning": "\033[93m{}\033[0m",
    "error": "\033[91m{}\033[0m",
}


def print_log(style, message):
    """Print in log format."""
    message = "{style}: {message}".format(style=style.upper(), message=message)
    print(colour[style].format(message))


def info(message):
    """Log in info colour."""
    print_log("info", message)


def debug(message):
    """Log in debug colour."""
    print_log("debug", message)


def warning(message):
    """Log in warning colour."""
    print_log("warning", message)


def error(message):
    """Log in error colour."""
    print_log("error", message)
