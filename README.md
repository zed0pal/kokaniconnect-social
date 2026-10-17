# Kokani Connect Social

Automated Instagram publishing for [@kokaniconnect_hub](https://www.instagram.com/kokaniconnect_hub/) — approved posts from Kokani Connect, scheduled via GitHub Actions.

## How it works

1. Every week Claude drafts the next week's posts from [kokaniconnect.com](https://kokaniconnect.com) and sends them for review.
2. Only posts Zuber approves are added to `queue/posts.json` with `"status": "approved"`, and their images to `media/`.
3. The **Publish to Instagram** workflow runs on **Saturday, Monday and Thursday at 2:30 PM KSA** and posts anything approved and due.
4. The **Refresh Instagram token** workflow renews the access token on the 1st and 15th of each month.

## Post statuses

| Status | Meaning |
|---|---|
| `draft` | Not reviewed. Never published. |
| `approved` | Will publish at its `scheduled_at` time. |
| `hold` | Paused. Change back to `approved` to release it. |
| `rejected` | Will not be published. |
| `published` | Done. `ig_media_id` records the Instagram post. |
| `failed` | Something went wrong. See `error`. |

**To stop a post at the last minute:** open `queue/posts.json` on GitHub, click the pencil icon, change that post's `"approved"` to `"hold"`, and commit.

`scheduled_at` is in UTC. 2:30 PM KSA = `11:30:00+00:00`.

## Secrets (Settings → Secrets and variables → Actions)

- `IG_ACCESS_TOKEN` — Instagram user access token
- `IG_USER_ID` — Instagram account ID
- `GH_PAT` — fine-grained token with Secrets read/write on this repo (used only to save the refreshed Instagram token)

Images are served publicly via GitHub Pages so Instagram can fetch them. Use JPEG, 1080×1350 (portrait) or 1080×1080 (square).
