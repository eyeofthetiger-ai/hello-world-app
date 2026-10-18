# Hello, world: EyeOfTheTiger test app

The smallest useful app for the EyeOfTheTiger app library. It shows your
EOT-1's live stream with **Hello, world.** written over it.

If you can see that, every part of the app path works: the app was built,
installed on your EOT-1, given its API key, opened from the portal with a
valid token, and can reach the live stream.

It's also a template. Click **Use this template** on GitHub to start your own
app from it.

## Try it

In the [portal](https://platform.eyeofthetiger.ai), click **Apps**, open
**Hello, world - test app**, click **Install** and pick your EOT-1. Then on
that EOT-1's page, click **Open** next to the app. The portal starts the
live stream and opens the app in a new tab.

It runs on `cpu-tiny` (1 vCPU, 512 MiB), the cheapest size, and is billed
per hour from your credits while it's running. Stop it from the EOT-1's page
when you're done.

## How it works

| File | What it does |
|---|---|
| [`app.py`](app.py) | A Python standard-library web server. Checks the portal's token, and fetches the live stream's playback URL with the EOT-1's API key so the key never reaches the browser. |
| [`index.html`](index.html) | Plays the live stream over WebRTC (WHEP) and puts "Hello, world." on top. |
| [`Dockerfile`](Dockerfile) | Builds the image. It must be at the root of the repository. |
| [`test_app.py`](test_app.py) | Tests for the token check and the endpoints: `python -m unittest test_app`. |

The platform gives every cloud app these environment variables:

| Variable | What it is |
|---|---|
| `CAMERA_API_URL` | The platform's base URL |
| `CAMERA_API_KEY` | An API key for the customer's EOT-1, sent as the `x-api-key` header |
| `CAMERA_ID` | The EOT-1 the app was installed for |
| `APP_NAME` | The name the app was installed under |
| `EMBED_TOKEN_SECRET` | The secret the portal's `?token=` is signed with |
| `PORT` | The port to listen on (set by Cloud Run) |

## Run it locally

With an API key from the portal (gear menu → **API keys**) and one of your
EOT-1 ids. Without `EMBED_TOKEN_SECRET` the token check is off.

```bash
docker build -t hello-world-app .
docker run --rm -p 8080:8080 \
  -e CAMERA_API_URL=https://platform.eyeofthetiger.ai \
  -e CAMERA_API_KEY=YOUR_API_KEY \
  -e CAMERA_ID=eot-a3f9c2d1 \
  hello-world-app
```

Start a live stream from your EOT-1's page in the portal, then open
http://localhost:8080.

## Make it your own

Keep the token check, `/status` and the `Dockerfile`, change the rest, then
submit it from **Apps → Submit an app** in the portal. The full guide is at
[docs.eyeofthetiger.ai/apps/marketplace](https://docs.eyeofthetiger.ai/apps/marketplace).
