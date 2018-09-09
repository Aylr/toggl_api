# Toggl

[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/ambv/black)

This library helps get and wrangle data from the toggl API.

## Installation

1. Clone repo
2. from the repo root directory run `make install`

## Use

You will need to either have a `config.yml` file with your toggl credentials or 
pass them at runtime.

Currently this pacakge works with only a single workspace. If you have more 
than one you'll need to specify that in the config file or at runtime.

### Config File Template

Create a file called `config.yml`

```yaml
email: "you@yourdomain.com"
toggl_api_key: "super_secret_toggl_api_key"
workspace_id: 12345
```
