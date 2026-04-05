# Intervals.icu MCP Server

Model Context Protocol (MCP) server for connecting Claude and ChatGPT with the Intervals.icu API. It provides tools for authentication and data retrieval for activities, events, and wellness data.

If you find the Model Context Protocol (MCP) server useful, please consider supporting its continued development with a donation.

## Requirements

- Python 3.12 or higher
- [Model Context Protocol (MCP) Python SDK](https://github.com/modelcontextprotocol/python-sdk)
- httpx
- python-dotenv

## Setup

### 1. Install uv (recommended)

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 2. Clone this repository

```bash
git clone https://github.com/mvilanova/intervals-mcp-server.git
cd intervals-mcp-server
```

### 3. Create and activate a virtual environment

```bash
# Create virtual environment with Python 3.12
uv venv --python 3.12

# Activate virtual environment
# On macOS/Linux:
source .venv/bin/activate
# On Windows:
.venv\Scripts\activate
```

### 4. Sync project dependencies

```bash
uv sync
```

### 5. Set up environment variables

Make a copy of `.env.example` and name it `.env` by running the following command:

```bash
cp .env.example .env
```

Then edit the `.env` file and set your Intervals.icu athlete id and API key:

```
API_KEY=your_intervals_api_key_here
ATHLETE_ID=your_athlete_id_here
MCP_AUTH_TOKEN=your_secret_token_here
```

`MCP_AUTH_TOKEN` is an optional shared secret used to protect the server when deployed remotely (e.g. on Render). Generate any random string — for example with `python -c "import secrets; print(secrets.token_urlsafe(32))"`. When set, all HTTP requests must include this token as a Bearer token in the `Authorization` header. When unset, the middleware is a no-op (suitable for local/stdio usage).

#### Getting your Intervals.icu API Key

1. Log in to your Intervals.icu account
2. Go to Settings > API
3. Generate a new API key

#### Finding your Athlete ID

Your athlete ID is typically visible in the URL when you're logged into Intervals.icu. It looks like:

- `https://intervals.icu/athlete/i12345/...` where `i12345` is your athlete ID

## Updating

This project is actively developed, with new features and fixes added regularly. To stay up to date, follow these steps:

### 1. Pull the latest changes from `main`

> ⚠️ Make sure you don’t have uncommitted changes before running this command.

```bash
git checkout main && git pull
```

### 2. Update Python dependencies

Activate your virtual environment and sync dependencies:

```bash
source .venv/bin/activate
uv sync
```

### Troubleshooting

If Claude Desktop fails due to configuration changes, follow these steps:

1. Delete the existing entry in claude_desktop_config.json.
2. Reconfigure Claude Desktop from the intervals_mcp_server directory:

```bash
mcp install src/intervals_mcp_server/server.py --name "Intervals.icu" --with-editable . --env-file .env
```

## Usage with Claude

### 1. Configure Claude Desktop

To use this server with Claude Desktop, you need to add it to your Claude Desktop configuration.

1. Run the following from the `intervals_mcp_server` directory to configure Claude Desktop:

```bash
mcp install src/intervals_mcp_server/server.py --name "Intervals.icu" --with-editable . --env-file .env
```

2. If you open your Claude Desktop App configuration file `claude_desktop_config.json`, it should look like this:

```json
{
  "mcpServers": {
    "Intervals.icu": {
      "command": "/Users/<USERNAME>/.cargo/bin/uv",
      "args": [
        "run",
        "--with",
        "mcp[cli]",
        "--with-editable",
        "/path/to/intervals-mcp-server",
        "mcp",
        "run",
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

Where `/path/to/` is the path to the `intervals-mcp-server` code folder in your system.

If you observe the following error messages when you open Claude Desktop, include the full path to `uv` in the command key in the `claude_desktop_config.json` configuration file. You can get the full path by running `which uv` in the terminal.

```
2025-04-28T10:21:11.462Z [info] [Intervals.icu MCP Server] Initializing server...
2025-04-28T10:21:11.477Z [error] [Intervals.icu MCP Server] spawn uv ENOENT
2025-04-28T10:21:11.477Z [error] [Intervals.icu MCP Server] spawn uv ENOENT
2025-04-28T10:21:11.481Z [info] [Intervals.icu MCP Server] Server transport closed
2025-04-28T10:21:11.481Z [info] [Intervals.icu MCP Server] Client transport closed
```

3. Restart Claude Desktop.

### 2. Use the MCP server with Claude

Once the server is running and Claude Desktop is configured, you can use the following tools to ask questions about your past and future activities, events, and wellness data.

- `get_activities`: Retrieve a list of activities
- `get_activity_details`: Get detailed information for a specific activity
- `get_activity_intervals`: Get detailed interval data for a specific activity
- `get_activity_streams`: Get time-series stream data (power, HR, cadence, etc.) for a specific activity
- `get_activity_histogram`: Get a power, heart rate, or pace histogram for a specific activity (pass `histogram_type` as `"power"`, `"hr"`, or `"pace"`)
- `get_athlete_power_curves`: Get best power output curves for selected durations and time periods
- `get_wellness_data`: Fetch wellness data
- `get_events`: Retrieve upcoming events (workouts, races, etc.)
- `get_event_by_id`: Get detailed information for a specific event

## Usage with ChatGPT

ChatGPT’s beta MCP connectors can also talk to this server over the SSE transport.

1. Start the server in SSE mode so it exposes the `/sse` and `/messages/` endpoints:

   ```bash
   export FASTMCP_HOST=127.0.0.1 FASTMCP_PORT=8765 MCP_TRANSPORT=sse FASTMCP_LOG_LEVEL=INFO
   python src/intervals_mcp_server/server.py
   ```

   The startup log prints the full URLs (for example `http://127.0.0.1:8765/sse`). ChatGPT needs that public URL, so forward the port with a tool such as `ngrok http 8765` if you are not exposing the server directly.

2. In ChatGPT, open **Settings → Features → Custom MCP Connectors** and click **Add**. Fill in:

   - **Name**: `Intervals.icu`
   - **MCP Server URL**: `https://<your-public-host>/sse`
   - **Authentication**: leave as _No authentication_ unless you have protected your tunnel.

   You can reuse the same `ngrok http 8765` tunnel URL here; just ensure it forwards to the host/port you exported above.

3. Save the connector and open a new chat. ChatGPT will keep the SSE connection open and POST follow-up requests to the `/messages/` endpoint announced by the server. If you restart the MCP server or tunnel, rerun the SSE command and update the connector URL if it changes.

## Deployment with Render

For production use or remote access from Claude on any device, you can deploy the server to Render as a Docker Web Service. This enables Claude to connect remotely without local setup.

### Prerequisites

1. A [Render](https://render.com) account
2. Your Intervals.icu API Key and Athlete ID (see the Setup section above)
3. The intervals-mcp-server repository on GitHub

### Deployment Steps

#### 1. Fork the Repository (if needed)

If you don't have write access to this repository, fork it to your GitHub account first.

#### 2. Create a New Web Service on Render

1. Go to [render.com](https://render.com) → **New** → **Web Service**
2. Connect your GitHub repository (`intervals-mcp-server` or your fork)
3. Configure the service:
   - **Name**: `intervals-mcp-server` (or your preferred name)
   - **Branch**: `main`
   - **Runtime**: **Docker**
   - **Port**: `8000`
   - **Health Check Path**: `/sse`

#### 3. Set Environment Variables

Your Intervals.icu credentials (`API_KEY` and `ATHLETE_ID`) are read from the `.env` file that is baked into the Docker image at build time — you do **not** need to add them as Render environment variables.

In the Render dashboard, under **Environment**, add the following variables:

| Key | Value | Description |
|-----|-------|-------------|
| `MCP_TRANSPORT` | `sse` | Use SSE transport instead of stdio |
| `FASTMCP_HOST` | `0.0.0.0` | Bind to all interfaces in container |
| `MCP_AUTH_TOKEN` | `your_secret_token` | Shared secret that clients must send as a Bearer token |

> **Important:** Set `MCP_AUTH_TOKEN` to the same value you generated during [Setup step 5](#5-set-up-environment-variables). Anyone with this token can access your server, so treat it like a password.

#### 4. Deploy and Verify

1. Click **Create Web Service** — Render will build the Docker image and deploy
2. Wait for the build to complete and health check to pass (green status)
3. Note your service URL: `https://your-service-name.onrender.com`
4. Test the SSE endpoint by opening `https://your-service-name.onrender.com/sse` in a browser
   - You should see a persistent `text/event-stream` connection

#### 5. Configure Claude to Use Your Deployed Server

**For Claude Web/Mobile (Recommended):**

1. Open Claude → **Settings** → **Integrations** (or **MCP Servers**)
2. Click **Add** (or **Connect apps**)
3. Fill in:
   - **Name:** `Intervals.icu`
   - **URL:** `https://your-service-name.onrender.com/sse`
   - **OAuth Token:** paste your `MCP_AUTH_TOKEN` value

Claude sends this token as a Bearer token in the `Authorization` header on every request. The server's `BearerTokenMiddleware` validates it before processing.

#### 6. Test the Integration

Open a new Claude conversation and ask:
> "What MCP tools do you have available?"

You should see tools like `get_activities`, `get_wellness_data`, `get_events`, etc. Then test with:
> "Fetch my recent activities from Intervals.icu"

### Troubleshooting Render Deployment

**Service won't start:**
- Check the Render logs for build errors
- Ensure all environment variables are set correctly
- Verify your Intervals.icu API key is valid

**Health check fails:**
- The `/sse` endpoint takes a few seconds to become available after startup
- Check that `FASTMCP_HOST=0.0.0.0` is set (required for Docker containers)

**Claude can't connect:**
- Verify your Render service URL is publicly accessible
- Ensure the URL ends with `/sse`
- Try opening the SSE endpoint in a browser to confirm it's working

**API errors:**
- Double-check your `ATHLETE_ID` and `API_KEY` environment variables
- Verify your Intervals.icu API key has necessary permissions

### Authentication

The server uses a **gate-guard** model to protect remote deployments:

- **Intervals.icu credentials** (`API_KEY`, `ATHLETE_ID`) are baked into the Docker image via the `.env` file and used by all API calls.
- **`MCP_AUTH_TOKEN`** is a separate shared secret that gates access to the server itself. When set, every HTTP request must include `Authorization: Bearer <MCP_AUTH_TOKEN>`. Requests without a valid token receive a `401 Unauthorized` response.
- **Local / stdio usage** does not require `MCP_AUTH_TOKEN`. When the variable is unset, the middleware is a no-op.

This keeps your Intervals.icu API key off the client side while still requiring a secret to reach the server.


## Development and testing

Install development dependencies and run the test suite with:

```bash
uv sync --all-extras
pytest -v tests
```

### Running the server locally

To start the server manually (useful when developing or testing), run:

```bash
mcp run src/intervals_mcp_server/server.py
```

#### Enabling debug logging

To capture server logs for debugging, wrap the command in a bash shell and redirect stderr to a file. Modify your `claude_desktop_config.json` like this:

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

Then tail the log file to see output in real-time:

```bash
tail -f /path/to/intervals-mcp-server/mcp-server.log
```

## License

The GNU General Public License v3.0

## Featured

### Glama.ai

<a href="https://glama.ai/mcp/servers/@mvilanova/intervals-mcp-server">
  <img width="380" height="200" src="https://glama.ai/mcp/servers/@mvilanova/intervals-mcp-server/badge" alt="Intervals.icu Server MCP server" />
</a>
