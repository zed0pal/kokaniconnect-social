#!/usr/bin/env python3
"""Publish approved, due posts from queue/posts.json to Instagram.

Uses the Instagram API with Instagram Login (graph.instagram.com).
Only posts with status "approved" and a scheduled_at time in the past are
published. Everything else (draft, hold, rejected, published, failed) is
left untouched. Safe to run repeatedly: a published post is never re-sent.

Env vars:
  IG_ACCESS_TOKEN  (secret)  Instagram user access token
  IG_USER_ID       (secret)  Instagram professional account ID
  MEDIA_BASE_URL   public base URL where media/ is served (GitHub Pages)
  IG_API_VERSION   optional, default v23.0
  DRY_RUN          "1" to print what would happen without calling Instagram
"""
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
QUEUE = ROOT / "queue" / "posts.json"
API = "https://graph.instagram.com/" + os.environ.get("IG_API_VERSION", "v23.0")
DRY_RUN = os.environ.get("DRY_RUN") == "1"


def call(method, path, params):
    data = urllib.parse.urlencode(params).encode()
    url = f"{API}/{path}"
    if method == "GET":
        req = urllib.request.Request(f"{url}?{data.decode()}")
    else:
        req = urllib.request.Request(url, data=data, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        raise RuntimeError(f"Instagram API {e.code} on {path}: {body}") from None


def wait_ready(container_id, token):
    """Instagram processes media asynchronously; wait until it's FINISHED."""
    for _ in range(30):
        s = call("GET", container_id, {"fields": "status_code", "access_token": token})
        code = s.get("status_code")
        if code == "FINISHED":
            return
        if code in ("ERROR", "EXPIRED"):
            raise RuntimeError(f"Container {container_id} status {code}")
        time.sleep(5)
    raise RuntimeError(f"Container {container_id} not ready after 150s")


def media_url(base, path):
    return f"{base.rstrip('/')}/{urllib.parse.quote(path.lstrip('/'))}"


def publish(post, user_id, token, base):
    images = post["images"]
    caption = post["caption"]
    if len(images) == 1:
        c = call("POST", f"{user_id}/media", {
            "image_url": media_url(base, images[0]),
            "caption": caption,
            "access_token": token,
        })["id"]
    else:
        children = []
        for img in images[:10]:
            cid = call("POST", f"{user_id}/media", {
                "image_url": media_url(base, img),
                "is_carousel_item": "true",
                "access_token": token,
            })["id"]
            wait_ready(cid, token)
            children.append(cid)
        c = call("POST", f"{user_id}/media", {
            "media_type": "CAROUSEL",
            "children": ",".join(children),
            "caption": caption,
            "access_token": token,
        })["id"]
    wait_ready(c, token)
    return call("POST", f"{user_id}/media_publish",
                {"creation_id": c, "access_token": token})["id"]


def main():
    token = os.environ.get("IG_ACCESS_TOKEN", "")
    user_id = os.environ.get("IG_USER_ID", "")
    base = os.environ.get("MEDIA_BASE_URL", "")
    if not DRY_RUN and not (token and user_id and base):
        sys.exit("Missing IG_ACCESS_TOKEN, IG_USER_ID or MEDIA_BASE_URL")

    queue = json.loads(QUEUE.read_text(encoding="utf-8"))
    now = datetime.now(timezone.utc)
    changed, failures, due_count = False, 0, 0

    for post in queue["posts"]:
        if post.get("status") != "approved":
            continue
        due = datetime.fromisoformat(post["scheduled_at"])
        if due > now:
            continue
        for img in post["images"]:
            if not (ROOT / img).is_file():
                raise SystemExit(f"{post['id']}: missing image file {img}")
        due_count += 1
        if DRY_RUN:
            print(f"[dry run] would publish {post['id']} ({len(post['images'])} image(s))")
            continue
        try:
            media_id = publish(post, user_id, token, base)
            post.update(status="published", ig_media_id=media_id,
                        published_at=datetime.now(timezone.utc).isoformat(timespec="seconds"))
            print(f"Published {post['id']} -> {media_id}")
        except Exception as e:  # keep going; record the error on the post
            post.update(status="failed", error=str(e)[:500])
            failures += 1
            print(f"FAILED {post['id']}: {e}", file=sys.stderr)
        changed = True

    if changed:
        QUEUE.write_text(json.dumps(queue, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    if not due_count:
        print("Nothing due.")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
