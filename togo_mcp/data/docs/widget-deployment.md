# Anonymous trial chat

The English landing page (`/`) and Japanese trial guidance (`/ja`) use the public
hub at https://hub.aibranch.org. The technical reference below the Japanese
trial guidance remains in English. No Google client ID or widget Rails server
is needed. Hub CORS must permit the deployment origin, and TogoMCP tools must
be active and public to anonymous visitors.

## Deploy on vhmcp

For the TogoMCP container, rebuild and restart the existing image from this
branch. The server serves `/ja` and the fixed widget asset path automatically.
For an independent static web server, publish `togomcp-intro.html` as `/index.html`,
`togomcp-intro-ja.html` as `/ja/index.html`, and `assets/llm-meta-widget.js` as
`/assets/llm-meta-widget.js`. Publish the adjacent license file as well.
Verify both language links and send a question at the actual deployment origin;
localhost and file URLs may be rejected by the public hub's CORS policy.

## Turning the chat off

Set `TOGOMCP_TRIAL_CHAT=0` (also `false`, `no` or `off`) in the server's environment
and re-create the container. Both pages are then served without the "Try TogoMCP chat"
panel and without the widget; the language links and the rest of the page are
unchanged. Unset, or any other value, leaves the chat on. `deploy.sh` forwards the
variable (`TOGOMCP_TRIAL_CHAT_TEST` for the test container), so no rebuild is needed.

The server removes everything between `<!-- TRIAL-CHAT:START -->` and
`<!-- TRIAL-CHAT:END -->`. Each page has two such regions, the panel and the widget.
Keep anything chat-specific inside them. A static web server ignores the variable:
delete the two regions by hand there.

## Configuration

Both pages select all active TogoMCP tools initially. Visitors can deselect tools.
The configured model is `qwen3-8-27b-fast`; choose another tool-capable model if
hub availability changes. `max-exchanges="4"` limits user submissions per
conversation. Set a positive integer such as `2` to change it. The widget shows
remaining submissions and disables input when exhausted. Reload preserves the
count; Clear starts a new conversation. Failed/cancelled submissions also count.
`max-rounds="10"` separately limits internal LLM/tool rounds per submission, including the final answer turn. Ten rounds allow schema lookup and query retries before summarizing results; completed answers stop earlier.
The browser limit can be reset or bypassed; enforce abuse protection and quotas
on the hub for production use.

## Bundled widget provenance

Source: https://github.com/yayamamo/llm_meta_widget/tree/d20130f
Built asset: `app/assets/javascripts/llm_meta_widget/llm-meta-widget.js`.
The adjacent Apache-2.0 license covers the widget; bundled dependencies retain
license comments in the asset. To update, build the pinned widget source with
`npm ci && npm run build`, copy its built asset and license, and verify both
language pages and conversation limits before committing.

## Launcher position

The page stylesheet places the chat launcher 96px above the bottom edge, plus
the device safe area, leaving the back-to-top button at its existing position.
Adjust `bottom` and `right` in `llm-meta-widget #llm-meta-widget-toggle` to move
the launcher. The scoped selector overrides the bundled widget stylesheet.
