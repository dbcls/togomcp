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
and re-create the container. Both pages are then served without the widget and
without the whole box under the hero: the "Try TogoMCP chat" panel and the
English / 日本語 links in it, which have nothing to point at once the chat is gone.
The rest of the page is unchanged. `/ja` still answers, but all of its Japanese is
in that box, so it then serves the English page. Unset, or any other value, leaves
the chat on. `deploy.sh` forwards the variable (`TOGOMCP_TRIAL_CHAT_TEST` for the
test container), so no rebuild is needed.

The server removes everything between `<!-- TRIAL-CHAT:START -->` and
`<!-- TRIAL-CHAT:END -->`. Each page has three such regions: the launcher's style
rule in `<head>`, the box under the hero and the widget. Keep anything chat-specific inside them.
A static web server ignores the variable: delete the three regions by hand there.

## Configuration

Both pages select all active TogoMCP tools initially. Visitors can deselect tools.
The configured model is `gpt-oss-120b` (set in the `model` attribute on both pages); choose another tool-capable model if
hub availability changes. `max-exchanges="4"` limits user submissions per
conversation. Set a positive integer such as `2` to change it. The widget shows
remaining submissions and disables input when exhausted. Reload preserves the
count; Clear starts a new conversation. Failed/cancelled submissions also count.
`max-rounds="10"` separately limits internal LLM/tool rounds per submission, including the final answer turn. Ten rounds allow schema lookup and query retries before summarizing results; completed answers stop earlier.
The browser limit can be reset or bypassed; enforce abuse protection and quotas
on the hub for production use.

## Bundled widget provenance

Source: https://github.com/yayamamo/llm_meta_widget/tree/89ade7f
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

## Updated widget and panel controls

This bundle merges upstream llm_meta_widget 0.12.2 through commit 1f7d80a,
including reader-follow scrolling and the finished-thinking-block Chromium
workaround. It retains the TogoMCP conversation limits and initial tool selection.
Both pages set `chat-title="TogoMCP Trial"`. Drag the top-left ⤢ handle to resize
while keeping the bottom/right edges anchored. Focus the handle and use arrow
keys for 32px adjustments. The preferred size survives closing and reloading;
viewport bounds prevent the panel from growing off screen.

The page model is unchanged by this UI update. If deploying llm_meta_server
PR #192's local-only anonymous policy, first switch the page model to an allowed
Ollama model and configure the matching ANONYMOUS_MODELS allowlist; the current
house-funded gpt-oss-120b configuration does not satisfy that policy.

## Limit-stop messages

When an internal round cap or a service resource limit stops processing, the
widget explains in Japanese/English that the reply may be incomplete and that
another attempt may take a different path and finish within the limits. It
suggests narrowing the question. Rate/capacity errors advise waiting (including
Retry-After when supplied), while daily quotas and operator stops require reset
or service resumption. There is no automatic retry after a resource-limit MCP
rejection; ordinary query errors can still be passed to the model for correction.
