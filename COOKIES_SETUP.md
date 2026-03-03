# YouTube Cookies Setup for Deployment

Render, Railway, Fly.io, and other cloud platforms use **datacenter IP addresses**
that YouTube identifies and blocks. The solution is to authenticate yt-dlp with your
own YouTube session cookies so requests come from a logged-in identity rather than
an anonymous server.

---

## Step 1 — Export your cookies

1. Open **Chrome** (or any Chromium browser) and sign into YouTube.
2. Install the extension **"Get cookies.txt LOCALLY"**
   ([Chrome Web Store](https://chrome.google.com/webstore/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc))
3. Navigate to **https://www.youtube.com**
4. Click the extension icon → select **youtube.com** → click **Export**
5. Save the file as `cookies.txt` (Netscape format — the default)

---

## Step 2 — Base64-encode the file

### Windows (PowerShell)
```powershell
[Convert]::ToBase64String([IO.File]::ReadAllBytes("cookies.txt")) | Set-Clipboard
```
(This copies the encoded string directly to your clipboard.)

### macOS / Linux
```bash
base64 -w 0 cookies.txt | pbcopy   # macOS – copies to clipboard
base64 -w 0 cookies.txt            # Linux  – prints to terminal, copy manually
```

---

## Step 3 — Add to Render

1. Go to your Render service → **Environment** tab
2. Click **Add Environment Variable**
3. Set:
   - **Key:** `YT_COOKIES_B64`
   - **Value:** *(paste the base64 string)*
4. Click **Save Changes** → Render will automatically redeploy

---

## Step 4 — Verify

After deployment, test with any YouTube URL. The error
*"YouTube is blocking this server"* should be gone.

If it reappears after a few weeks, your session may have expired — re-export
cookies and update the env var.

---

## Alternative: PO Token (advanced)

If you don't want to share account cookies, you can use yt-dlp's Proof-of-Origin
token instead. This is more complex to obtain but doesn't require a logged-in session.

Set both env variables:
```
YT_PO_TOKEN     = <your po_token>
YT_VISITOR_DATA = <your visitor_data>
```

See [yt-dlp wiki: PO Token](https://github.com/yt-dlp/yt-dlp/wiki/Extractors#po-token-guide).

---

## Security note

`cookies.txt` contains your YouTube session — treat it like a password.
- Do **not** commit it to Git (add to `.gitignore`)
- Render stores env vars encrypted at rest
- Consider using a secondary Google account for this purpose
