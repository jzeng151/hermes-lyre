# hermes-lyre

This repository holds Lyre, a Hermes plugin that makes Hermes replies easy to follow with a screen reader.

The plugin and its documentation are in the [lyre](lyre/README.md) folder.

## Development

The plugin uses only the Python standard library. Tests need pytest and PyYAML.

Run the tests from the plugin folder:

    cd lyre
    uv run --no-project --with pytest --with pyyaml pytest

Lint with the same ruff version and core rules Hermes uses (config in `ruff.toml`):

    uvx ruff@0.15.10 check .

Check the plugin the way the Hermes catalog does:

    hermes plugins validate lyre
    hermes plugins doctor lyre --ci

## Layout

Each plugin is a top-level folder with its own plugin.yaml, README, LICENSE and tests, the same layout as the official Hermes plugin repositories. The catalog entry points at it with `subdir: lyre`.
