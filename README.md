# Lyre

Lyre is a Hermes plugin that makes Hermes replies easy to follow with a screen reader.

It is in early development and does not change any replies yet.

## Development

Run the tests:

    uv run pytest

Check the plugin the way the Hermes catalog does:

    hermes plugins validate lyre
    hermes plugins doctor lyre --ci
