# Intervals.icu MCP Server

Model Context Protocol (MCP) server for connecting Claude and ChatGPT with the Intervals.icu API. It provides tools for retrieving activities, events, wellness data, power curves, and more.

If you find the MCP server useful, please consider supporting its continued development with a donation.

## Prerequisites

Before you begin you'll need your Intervals.icu credentials:

1. **API Key** — Log in to [Intervals.icu](https://intervals.icu), go to **Settings → API**, and generate a new API key.
2. **Athlete ID** — Visible in the URL when you're logged in, e.g. `https://intervals.icu/athlete/i12345/...` → `i12345`.

## Setup — Deploy to Render (recommended)

The fastest way to get started is to deploy the server to [Render](https://render.com) as a Docker Web Service. No local installation required.

### 1. Create a Web Service on Render

1. Go to [render.com](https://render.com) → **New** → **Web Service**
2. Connect your GitHub repository (`intervals-mcp-server` or your fork)
3. Configure the service:
   - **Name**: `intervals-mcp-server` (or your preferred name)
   - **Branch**: `develop`
   - **Runtime**: **Docker**
   - **Instance Type**: Free tier works fine

> **💤 Free tier cold starts:** Render free-tier services sleep after 15 minutes of inactivity. The first request after sleeping may take 30–60 seconds while the container restarts. Subsequent requests are fast. To avoid this, upgrade to a paid instance or use an external cron/ping service to keep it awake.

### 2. Set Environment Variables

In the Render dashboard under **Environment**, add:

| Key | Value | Description |
|-----|-------|-------------|
| `MCP_TRANSPORT` | `http` | Enables the remote transport (streamable HTTP) |
| `FASTMCP_HOST` | `0.0.0.0` | Bind to all interfaces (required inside Docker) |
| `FASTMCP_PORT` | `8000` | Port the server listens on |
| `ATHLETE_ID` | `your_athlete_id` | Your Intervals.icu athlete ID (e.g. `i12345`) |
| `API_KEY` | `your_api_key` | Your Intervals.icu API key |

### 3. Deploy and Verify

1. Click **Create Web Service** — Render will build the Docker image and deploy
2. Wait for the build to complete (green status)
3. Note your service URL: `https://your-service-name.onrender.com`
4. Test by opening `https://your-service-name.onrender.com/mcp` in a browser — you should get a response from the server

> **⚠️ Security Warning:** Claude does not currently authenticate when connecting to remote MCP servers. This means your Render endpoint is publicly accessible — anyone who discovers the URL can query and **mutate** your Intervals.icu data (e.g. create/update events). Do not share your service URL publicly. If this is a concern, use the [Local Setup](#local-setup-alternative) instead, which keeps everything on your machine behind stdio.

## Connecting Claude

1. Open Claude → **Settings** → **Integrations** (or **MCP Servers**)
2. Click **Add**
3. Fill in:
   - **Name:** `Intervals.icu`
   - **URL:** `https://your-service-name.onrender.com/mcp`

Open a new conversation and ask "What MCP tools do you have available?" to confirm the connection.

## Connecting ChatGPT

1. In ChatGPT, open **Settings → Features → Custom MCP Connectors** → **Add**
2. Fill in:
   - **Name**: `Intervals.icu`
   - **MCP Server URL**: `https://your-service-name.onrender.com/mcp`

Save the connector and open a new chat.

## Available Tools

Once connected, the following tools are available:

**Activities**
- `get_activities` — Retrieve a list of activities
- `get_activity_details` — Get detailed information for a specific activity
- `get_activity_intervals` — Get interval data for a specific activity
- `get_activity_streams` — Get time-series stream data (power, HR, cadence, etc.)
- `get_activity_histogram` — Get a power, heart rate, or pace histogram
- `get_activity_messages` — Get messages/comments on an activity
- `add_activity_message` — Add a message/comment to an activity

**Events**
- `get_events` — Retrieve upcoming events (workouts, races, etc.)
- `get_event_by_id` — Get detailed information for a specific event
- `add_or_update_event` — Create or update an event
- `delete_event` — Delete a specific event
- `delete_events_by_date_range` — Delete events within a date range

**Wellness & Training**
- `get_wellness_data` — Fetch wellness data
- `get_training_summary` — Get a training load summary
- `get_athlete_power_curves` — Get best power output curves for selected durations and time periods
- `get_athlete_zones` — Get athlete training zones (power, HR, pace, etc.)

**Custom Items**
- `get_custom_items` — List custom items
- `get_custom_item_by_id` — Get a specific custom item
- `create_custom_item` — Create a new custom item
- `update_custom_item` — Update an existing custom item
- `delete_custom_item` — Delete a custom item

**Workout Library**
- `get_workout_folders` — Get workout library folder metadata (IDs, names, types)
- `list_workouts` — List workouts in the library, optionally filtered by folder
- `get_workout` — Get full workout detail including step-by-step structure
- `create_workout` — Create a new workout in a library folder
- `update_workout` — Update an existing library workout

## Troubleshooting Render Deployment

- **Service won't start** — Check Render logs for build errors. Ensure all environment variables are set.
- **Claude/ChatGPT can't connect** — Verify the URL ends with `/mcp` and is publicly accessible. Try opening it in a browser.
- **API errors** — Double-check your `ATHLETE_ID` and `API_KEY` values. Verify your Intervals.icu API key is valid.
- **Free tier cold starts** — Render free-tier services sleep after inactivity. The first request may take 30–60 seconds to wake up.

---

<details>
<summary><strong>Local Setup (alternative)</strong></summary>

If you prefer to run the server on your own machine instead of Render, follow the steps below.

### Requirements

- Python 3.12 or higher
- [uv](https://github.com/astral-sh/uv) (recommended package manager)

### 1. Install uv

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 2. Clone and install

```bash
git clone https://github.com/mvilanova/intervals-mcp-server.git
cd intervals-mcp-server
uv venv --python 3.12
source .venv/bin/activate   # Windows: .venv\Scripts\activate
uv sync
```

### 3. Set up environment variables

```bash
cp .env.example .env
```

Edit `.env` and fill in your credentials:

```
API_KEY=your_intervals_api_key_here
ATHLETE_ID=your_athlete_id_here
```

### Configure Claude Desktop

1. From the project directory, run:

   ```bash
   mcp install src/intervals_mcp_server/server.py --name "Intervals.icu" --with-editable . --env-file .env
   ```

2. Your `claude_desktop_config.json` should look like:

   ```json
   {
     "mcpServers": {
       "Intervals.icu": {
         "command": "/Users/<USERNAME>/.cargo/bin/uv",
         "args": [
           "run",
           "--with", "mcp[cli]",
           "--with-editable", "/path/to/intervals-mcp-server",
           "mcp", "run",
           "/path/to/intervals-mcp-server/src/intervals_mcp_server/server.py"
         ],
         "env": {
           "INTERVALS_API_BASE_URL": "https://intervals.icu/api/v1",
           "ATHLETE_ID": "<YOUR_ATHLETE_ID>",
           "API_KEY": "<YOUR_API_KEY>",
           "LOG_LEVEL": "INFO"
         }
       }
     }
   }
   ```

   Replace `/path/to/` with the actual path. If you see `spawn uv ENOENT` errors, use the full path from `which uv`.

3. Restart Claude Desktop.

### Configure ChatGPT (local)

1. Start the server in HTTP mode:

   ```bash
   export FASTMCP_HOST=127.0.0.1 FASTMCP_PORT=8765 MCP_TRANSPORT=http FASTMCP_LOG_LEVEL=INFO
   python src/intervals_mcp_server/server.py
   ```

2. ChatGPT needs a public URL, so forward the port (e.g. `ngrok http 8765`).

3. In ChatGPT, open **Settings → Features → Custom MCP Connectors** → **Add**:
   - **Name**: `Intervals.icu`
   - **MCP Server URL**: `https://<your-public-host>/mcp`

### Updating

```bash
git checkout main && git pull
source .venv/bin/activate
uv sync
```

If Claude Desktop fails after an update, delete the entry in `claude_desktop_config.json` and re-run the `mcp install` command above.

### Enabling debug logging

Modify `claude_desktop_config.json` to redirect stderr to a log file:

```json
{
  "mcpServers": {
    "Intervals.icu": {
      "command": "/bin/bash",
      "args": [
        "-c",
        "/Users/<USERNAME>/.local/bin/uv run --with 'mcp[cli]' --with-editable /path/to/intervals-mcp-server mcp run /path/to/intervals-mcp-server/src/intervals_mcp_server/server.py 2>> /path/to/intervals-mcp-server/mcp-server.log"
      ],
      "env": {
        "INTERVALS_API_BASE_URL": "https://intervals.icu/api/v1",
        "ATHLETE_ID": "<YOUR_ATHLETE_ID>",
        "API_KEY": "<YOUR_API_KEY>",
        "LOG_LEVEL": "INFO"
      }
    }
  }
}
```

Then tail the log:

```bash
tail -f /path/to/intervals-mcp-server/mcp-server.log
```

</details>

## Development and testing

Install development dependencies and run the test suite with:

```bash
uv sync --all-extras
pytest -v tests
```

### Running the server locally

```bash
mcp run src/intervals_mcp_server/server.py
```

## License

The GNU General Public License v3.0

## Featured

### Glama.ai

<a href="https://glama.ai/mcp/servers/@mvilanova/intervals-mcp-server">
  <img width="380" height="200" src="https://glama.ai/mcp/servers/@mvilanova/intervals-mcp-server/badge" alt="Intervals.icu Server MCP server" />
</a>
