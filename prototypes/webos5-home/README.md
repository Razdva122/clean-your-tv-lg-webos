# Settings-only Home recovery on webOS 5.x

Run `python -m unittest discover -s prototypes/webos5-home` from the repository
root. The transport in these tests operates on a temporary file. The prototype
has no TV adapter, LS2 calls, boot registration or package entry point.

The factory Home handler on LG 65NANO913NA, firmware 04.64.00, follows
`getLaunchDefaultApp.home` on a short press. A custom assignment therefore
outlives the assigning process. The factory long-press branches handle only
LG Ribbon and LG Fullscreen. [Home Chooser's settings research][hc] documents
this family of firmware. [Issue #710][issue] tracks the volatile CYTV route.

The prototype saves the exact LG destination before submitting a custom
assignment. A separate process can use that journal after the writer dies.
Restore latches Stop before writing, keeps the latest unrelated defaults and
refuses to overwrite a foreign Home choice. A reply lost after a completed
write is reconciled through readback. The fixtures terminate a writer after
committing the settings change and before it can acknowledge it. With a
possibly outstanding activation, reading the original stock value cannot
complete Stop. With a possibly outstanding rollback, a second rollback
submission is refused until the original outcome is known.

The temporary-file simulation has synchronous commits and no compositor cache.
A live adapter needs to establish when a timed-out settings mutation has
settled and when the stock key handler sees the restored value. A pending
activation could otherwise commit after recovery already read the stock value.
External settings writers also do not share the CYTV lock. Production
integration needs an independently supervised Stop and recovery path, including
startup before Home is usable, and hardware acceptance for short and long Home.
Keeping the Settings write out of the shipped backend preserves the existing
volatile fallback while those assumptions are tested.

[hc]: https://github.com/webosbrew/home-chooser/blob/v0.2.0/docs/settings-app.md#which-stock-home
[issue]: https://github.com/Razdva122/clean-your-tv-lg-webos/issues/710
