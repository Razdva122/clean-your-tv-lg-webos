# Ruska for webOS

Ruska depicts a Finnish autumn dusk over a lake. The wallpaper and theme
settings originate from [Gathin23/cleanyourtv](https://github.com/Gathin23/cleanyourtv/tree/3f43140f9ecaf12cdc84be1487fd2eec09c02c9f/themes/ruska),
licensed under MIT (see LICENSE). The falling leaves are part of the illustration,
not an animated overlay.

Set `theme: "ruska"` in `launcher/config.js` before building a personalized Home
package. Follow the existing manual build/install guide. Leave `columns`,
`dockApps`, and `hiddenApps` as desired; the theme preserves those choices.

The webOS adaptation uses the original wallpaper and background color, a 70%
opaque dock, app-colored focus glow, no ambient glow over the artwork, and
focus transitions without overshoot. It changes no remote handling, services,
permissions, or network access. Assets are bundled and loaded locally.

To revert, remove `theme` from the configuration and rebuild, or reinstall a
previously saved personalized Home package without uninstalling first.
