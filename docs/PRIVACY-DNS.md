# Filter DNS for an LG TV without root

You can filter advertising and tracking domains on your home network with either CYTV edition, or with stock LG Home. CYTV does not change the TV’s DNS settings. You need the TV remote and either a DNS filtering service or an always-on device on your LAN.

[Русский](PRIVACY-DNS.ru.md) · [Privacy controls on the TV](PRIVACY.md) · [CYTV network activity](CYTV-NETWORK.md)

## 1. Prepare a filter

Choose one option. Start with a TV-specific profile or a resolver used only by the TV so you can undo a rule without disrupting other devices.

| Option | What to configure |
| --- | --- |
| AdGuard Home on your network | Give the server a stable LAN address. Under **Filters → DNS blocklists**, add the [HaGeZi LG webOS list](https://raw.githubusercontent.com/hagezi/dns-blocklists/main/adblock/native.lgwebos.txt) as a custom list. Enable it and confirm the download succeeded. [AdGuard Home setup](https://adguard-dns.io/kb/adguard-home/getting-started/) |
| Pi-hole on your network | Give Pi-hole a stable LAN address. Under **Domains**, add an exact deny entry for each hostname you want to block. Two starting points are LG advertising (`ad.lgappstv.com`) and Alphonso (`prov-lg.alphonso.tv`). If other devices use Pi-hole, assign the rules and the TV client to a dedicated group. [Pi-hole setup](https://docs.pi-hole.net/main/post-install/) |
| NextDNS hosted service | Create a profile for the TV. In **Denylist**, add the two hostnames above, one per entry. Open **Setup** and use the addresses for that profile. For plain IPv4, follow **Linked IP** and refresh the association if your home’s public IP changes. NextDNS receives the queried domains and your public IP. Choose how long to retain query logs in **Settings**. [NextDNS dashboard](https://my.nextdns.io/) |

## 2. Point the TV at the filter

1. Before changing anything, take a photo of the active connection settings, including the automatic setting, address, subnet mask, gateway and DNS. Check that a streaming app and the LG store open.
2. If your router supports per-device DNS, assign the filtered DNS to the TV there and reconnect the TV. A router-wide DHCP change also affects other clients. For manual setup on the TV, open **All Settings** and follow the route for the installed webOS version. [LG’s illustrated DNS instructions](https://www.lg.com/us/support/help-library/manual-dns-settings-webos-CT10000020-20150576570174)

   | webOS | Menu |
   | --- | --- |
   | 6 and later (2021 onward) | General → Network |
   | 5 (2020) | Connection → Network Connection Settings |
   | 4.5 (2019) | Connection |
   | 4 and earlier (2018 and older) | Network, if available |

3. Select the active wired connection or **Wi-Fi Connection → Advanced Wi-Fi Settings**, then **Edit**. If disabling **Set Automatically** also makes the TV address manual, reserve its current address in the router first. Keep the subnet mask and gateway. Enter your filtering server’s address under **DNS Server** and save. If the TV has no DNS field, use the router method.
4. If the network supplies IPv6 DNS or a secondary DNS address, make sure each resolver offered to the TV applies the same rules. A guest network with client isolation can prevent the TV from reaching a local resolver, the installer or a casting device.

## 3. Verify from the TV and undo a change

Open `example.org` in the **TV browser**. Find that query in the resolver’s log. Temporarily block that exact name, revisit after the cached answer expires, and check for a **blocked** entry. Remove the test rule. If the router forwards all queries under its own address, use the time of the TV visit to match the request. Disable logging afterwards if you prefer.

Try the store, streaming, sign-in, clock and the LG update check. In No-root, check the Developer Mode timer and renewal if you use it. If a feature fails, disable the most recent rule or list, reconnect and retry. Use the log to allow only the hostname the feature needs. Broad rules for `lge.com` or `lgtvsdp.com` can affect several services.

To undo the DNS change, restore **Set Automatically** or the original manual values from your photo, or revert the TV’s router policy. Reconnect and repeat the same checks. A DNS log shows domain lookups. Apps using cached addresses, direct IP connections or their own encrypted DNS can bypass the filter.
