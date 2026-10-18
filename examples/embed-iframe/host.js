// SPDX-License-Identifier: Apache-2.0
// The embedding page. It asks ITS OWN server for a session (the API key never reaches the browser), frames the hosted checkout and listens for the
// experimental messages of packages/sdk/src/embed.js.
import { FRAME_ATTRIBUTES, acceptEmbedMessage, buildFrameUrl } from "/embed.js";

const log = document.getElementById("log");
const lines = [];
const note = (text) => {
  lines.push(text);
  log.textContent = lines.join("\n");
};

const { sessionId, checkoutBaseUrl, checkoutOrigin } = await (await fetch("/session", { method: "POST" })).json();
const iframe = document.createElement("iframe");
iframe.title = "Checkout";
for (const [name, value] of Object.entries(FRAME_ATTRIBUTES)) iframe.setAttribute(name, value);
iframe.src = buildFrameUrl({ checkoutBaseUrl, sessionId });
document.getElementById("frame").append(iframe);
note(`framed ${iframe.src}`);

window.addEventListener("message", (event) => {
  const msg = acceptEmbedMessage(event, { checkoutOrigin, frameWindow: iframe.contentWindow, sessionId });
  if (msg === null) {
    note(`ignored a message from ${event.origin}`);
    return;
  }
  note(`accepted ${JSON.stringify(msg)}`);
  if (msg.type === "resize") iframe.style.height = `${msg.height}px`;
});
