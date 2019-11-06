# sublime-shadowenv

Loads the [Shadowenv](https://shopify.github.io/shadowenv) from a project when editing it.

# Installation

Can be installed via PackageControl or manually:

```
git clone https://github.com/Shopify/sublime-shadowenv ~/Library/Application\ Support/Sublime\ Text\ 3/Packages/sublime-shadowenv
```

# Usage

When there's a Shadowenv present in the project, it will be loaded automatically.

Note that environment changes will be applied when you open a project, but they will be applied
across all windows, so working on multiple projects at the same time will end up with both projects
sharing the environment of the most-recently-opened.

# TODO/bugs

* Reload automatically after running shadowenv trust
* Watch for shadowenv changes
