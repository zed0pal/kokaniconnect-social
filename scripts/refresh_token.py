#!/usr/bin/env python3
"""Refresh the long-lived Instagram token (valid 60 days) and save it back
to the IG_ACCESS_TOKEN repo secret. Prints nothing secret.

Env vars: IG_ACCESS_TOKEN (secret), GH_TOKEN (the GH_PAT secret),
GITHUB_REPOSITORY (set by GitHub Actions).
"""
import json
import os
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request

token = os.environ["IG_ACCESS_TOKEN"]
url = "https://graph.instagram.com/refresh_access_token?" + urllib.parse.urlencode(
    {"grant_type": "ig_refresh_token", "access_token": token})
try:
    with urllib.request.urlopen(url, timeout=60) as r:
        data = json.loads(r.read())
except urllib.error.HTTPError as e:
    sys.exit(f"Refresh failed ({e.code}): {e.read().decode(errors='replace')}")

new_token = data["access_token"]
days = int(data.get("expires_in", 0)) // 86400
subprocess.run(
    ["gh", "secret", "set", "IG_ACCESS_TOKEN", "--repo", os.environ["GITHUB_REPOSITORY"]],
    input=new_token.encode(), check=True)
print(f"Token refreshed and saved. Valid for about {days} days.")
