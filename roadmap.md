## Roadmap: Refactoring Evernote2Obsidian

1. Fix bug found during development of tests for UI
1. Create tests for menu UI
1. Correct code smells identified during planning of tests
1. Restructure as a PIP package
1. Create separate command line entry points
  - For `evernote2obsidian`
  - For an overall CLI entry point (which initially just calls `evernote2obsidian`)
1. Refactor current `main` entry point in `evernote2obsidian` to separate concerns:
  - menu handling
  - configuration setting
  - configuration reading
  - processing
1. Create subcommands to overall CLI entry point
  - Display menu, set configuration, and run `evernote2obsidian` subcommands (in other words, a synonym for what `evernote2obsidian` currently does)
  - Display menu and set configuration, but don't run anything
  - Print configuration
  - List notebooks
  - Run scan
  - Run export
    - To HTML
    - To Markdown
1. Move subcommands to a separate subdirectory, with automatic discovery
1. Add incremental subcommands
  - Export one note (or a set of notes?)
  - Display information about a note
1. Refactor `evernote2md`
  - Use subtype polymorphism to process different kinds of nodes