from conda import plugins

from .main import plugin_hook_implementation, COMMANDS

@plugins.hookimpl
def conda_post_commands():
    yield plugins.CondaPostCommand(
        name="conda-checkpoints-post-command",
        action=plugin_hook_implementation,
        run_for=COMMANDS,
    )