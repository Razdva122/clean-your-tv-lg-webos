# A focused Home layout

For a personalized launcher package, optionally set `homeApps` in
`launcher/config.js` to an ordered array of app IDs already present in the
packaged inventory. HDMI inputs use their launchable app IDs, not the IDs of
streaming applications.

Home shows only that selection. Duplicate and unavailable IDs are ignored.
The cards are centered while retaining the configured column size, with labels
instead of a large hero title. The Add app card and tile editing are omitted;
clock and top controls remain available. An empty selection focuses the top
controls. The Inputs menu continues to use the packaged input inventory.

This is a display configuration: no app is uninstalled, no HDMI port is disabled,
and saved ordinary app ordering and hiding preferences are preserved. To restore
the ordinary launcher, remove `homeApps` and rebuild, or reinstall the previous
personalized package without uninstalling first.
