// Client screen for the full-plugin example.
//
// The exact runtime API the Host exposes to a plugin screen is Host-provided and
// out of scope for spec v0.1.0 (see spec §6.1). This file shows the *shape* of a
// screen module: it renders into its own root element and talks only to its own
// namespaced routes (/api/plugins/full-plugin/...). Keep all DOM and CSS scoped to
// the plugin's root so nothing leaks into the rest of the app.

const PLUGIN_ID = "full-plugin";

export async function mount(root) {
  root.innerHTML = `
    <section class="full-plugin">
      <h2>Full Example Plugin</h2>
      <p>Color: <strong data-role="color">…</strong></p>
    </section>
  `;

  try {
    const res = await fetch(`/api/plugins/${PLUGIN_ID}/settings`);
    const settings = await res.json();
    root.querySelector('[data-role="color"]').textContent = settings.color;
  } catch (err) {
    // Fail soft: a fetch failure degrades the screen, it doesn't crash the plugin.
    console.warn(`${PLUGIN_ID}: could not load settings`, err);
  }
}
