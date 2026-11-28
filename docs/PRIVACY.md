# LG TV privacy and advertising settings

[Русский](PRIVACY.ru.md) · [DNS and home network](PRIVACY-DNS.md) · [What Clean Your TV connects to](CYTV-NETWORK.md)

You can change LG’s privacy choices with the TV remote, including on a TV without Clean Your TV. Start with **Viewing Information** and **Live Plus** if you want to limit viewing recognition. Start with **Home Promotion** if you want to hide a banner on LG Home. Ads that a streaming app or an HDMI device puts into its own picture have separate controls.

Press **Settings** (the gear), then **All Settings**. Look for the model code on the TV label and the installed webOS version in **TV Information**. A TV may have received a newer webOS since purchase. Use the row matching the menus you see. Note the previous choice before changing it, save or confirm if asked, then reopen the menu to check the result. The [LG manuals search](https://www.lg.com/us/support/manuals-documents) accepts the full model code.

<a id="viewing"></a>

## Viewing recognition and user agreements

**Live Plus** uses automatic content recognition (ACR) to identify programmes on supported inputs. This can include broadcasts and an HDMI box even when you never open LG Home. An independent study found that opting out stopped traffic to the ACR servers on the LG TVs tested. LG describes other purposes, such as personalised ads, as separate choices. [LG’s privacy explanation](https://www.lg.com/global/newsroom/news/statements/statement-understanding-privacy-on-lg-smart-tvs/) · [ACM IMC study](https://arxiv.org/abs/2409.06203)

Start each path below in **All Settings** unless the row specifies an older menu. On sets that offer both controls, switch **Live Plus** off and withdraw the optional **Viewing Information** agreement. If only the agreement appears, change it there.

| TV or menu generation | Where to look for Live Plus | Where to open User Agreements |
| --- | --- | --- |
| Older Smart TV before webOS | On the US models covered by LG’s 2012/13 LivePlus notice, open Settings from Smart Home or the Quick Menu → Smart TV settings (toolbox icon) → LivePlus → Off. | For other systems or markets, consult the model manual for viewing or data-collection options. |
| Early webOS through 2019, including webOS 4.5 | General → Additional Settings → Live Plus. On older layouts check General directly. | General → About This TV → User Agreements. On some versions User Agreements appears directly under General. |
| 2020, webOS 5.0 | General → Additional Settings → Live Plus, if listed. | Support → Additional Settings → User Agreements. |
| 2021–2024, webOS 6.0 and webOS 22–24 | General → System → Additional Settings → Live Plus. Some regional versions omit this switch. | Support → Privacy & Terms → User Agreements. |
| 2025, webOS 25 | Open the Viewing Information agreement first. If the TV also lists Live Plus in General → System → Additional Settings, turn it off there. | Support → Privacy & Terms → User Agreements. |
| 2026, webOS 26 | System → Additional Settings → Live Plus, if listed. | Support → Privacy & Terms → User Agreements. If Privacy & Terms appears at the top level, open it there. |

Model-year routes combine [LG’s generation-specific instructions](https://www.lg.com/it/supporto/supporto-prodotto/risoluzione-anomalie/help-library/cs-CT52001071-20153387508381/), [LG’s older US LivePlus guide, p. 5](https://www.lg.com/us/support/data/notice/USNTC130817102920/Smart%20TV%20LivePlus%20Support.pdf#page=5), [LG’s webOS 26 guide](https://kr.eguide.lgappstv.com/manual/w26_tv/w26_t04/engb.html) and the [original CleanYourTV LG walkthrough](https://cleanyour.tv/not-android#lg-2025). A missing switch leaves the TV’s setting unknown until you find its agreement or a model-specific explanation.

In **User Agreements**, open the individual choices. Keep the items your TV marks required for the smart services you use, commonly **Terms of Use** and **Privacy Policy**. Review these optional items where offered:

- Clear **Viewing Information** to withdraw viewing-data consent. Clear **Who.Where.What?** if you do not want the feature that identifies items in a programme.
- Clear **Voice Information** if you do not use LG voice recognition. To keep voice search with the remote button while disabling the wake word, leave that agreement enabled and follow the microphone steps below.
- Clear **Interest-based & Cross-device Advertising** and **Marketing Communications** if you do not want these uses. Where offered, enable **Do Not Sell My Personal Information** to opt out of sale.
- Apply your choices. If the agreements fail to load, check the TV’s internet connection and that **LG Services Country** matches your actual region. If an app asks for an agreement later, read which item it needs and restore only the consent you choose. [LG agreement support](https://www.lg.com/us/support/help-library/lg-tv-how-to-agree-to-the-user-agreements-CT10000018-20155154186594)

### Hands-free voice and the microphone

On supported sets open **General → AI Service → Voice Recognition Settings** and turn **Use Hands-free Voice Control** off. If your menus have moved, look up “hands-free” in the TV’s User Guide. When enabled, the TV can listen for its wake word in standby. LG says wake-word detection runs locally. For a physical cutoff, use the TV’s microphone switch if your model has one. The Magic Remote has its own microphone: with voice recognition enabled, pressing its voice button can still start a voice request. To restore hands-free operation, enable the microphone, the voice agreement and the hands-free setting. [LG Magic Remote instructions](https://www.lg.com/us/support/pdf/remotes/2023-Magic-Remote-MR23.pdf) · [LG microphone and standby behaviour](https://www.lg.com/global/newsroom/news/statements/statement-understanding-privacy-on-lg-smart-tvs/)

<a id="advertising"></a>

## Advertising cookies, tracking and the ad ID

Open **Advertisement** using your TV’s menus. Up to webOS 5.0, look in **General → Additional Settings** or **General**. On webOS 6.0/22 use **General → System → Additional Settings**. On webOS 23–26 try **Support → Privacy & Terms** first. If a route differs, search the TV’s User Guide for **Advertisement**. [LG advertising settings by generation](https://www.lg.com/it/supporto/supporto-prodotto/risoluzione-anomalie/help-library/cs-CT52001071-20153387508381/)

1. Turn **Limit Ad Tracking** **on**. If **Advertising Cookies** appears, turn it **off**.
2. If you also want a new advertising identifier, choose **Reset Ad ID**. Resetting replaces the old ID permanently. Leave tracking limited after resetting.
3. If **Advertisement** is missing, use the interest-based and cross-device advertising choice in [User Agreements](#viewing). These choices limit targeting. You may still see ads.

<a id="home-promotions"></a>

## Sponsored banners and recommendations on LG Home

Open **Home Settings**, then turn off **Home Promotion** for the sponsored banner and **Content Recommendation** for the recommendations where present. Open LG Home again to check the area you changed.

| Menus on the TV | Path from All Settings to Home Settings |
| --- | --- |
| 2019 webOS 4.5 | General → Additional Settings → Home Settings. Earlier models may lack these options. |
| 2020 webOS 5.0 | General → Home Settings. If your version groups it under Additional Settings, look there. |
| 2021–2025 | General → System → Additional Settings → Home Settings. |
| 2026 webOS 26 | System → Additional Settings → Home Settings. |

**Power On Screen** chooses what opens when the TV starts. Keep this setting and **Home Auto Launch** at their current values when removing promotions. For example, the CYTV Root native startup feature requires **Home Auto Launch** on or **Power On Screen → Home**. Choosing the last input can change which screen appears on wake. To undo an accidental change, restore the previous startup choice. [LG Home promotion settings](https://www.lg.com/eg_en/support/product-support/troubleshoot/help-library/cs-CT52008151-20153529296686/) · [LG startup-screen guide](https://www.lg.com/us/support/help-library/how-to-set-the-startup-screen-on-your-lg-tv-CT10000030-20155412183664) · [CYTV startup behaviour](../root-edition/README.md#candidate-native-startup-choices)

<a id="screensaver"></a>

## Ads on the LG screen saver

On some webOS 24 sets, **Screen Saver Promotion** is directly under **General → System → Additional Settings**. On supported webOS 25 TVs open **General → System → Additional Settings → Screen Saver Settings**. On webOS 26 start at **System → Additional Settings**. Set **Screen Saver Promotion** to **Off**. Leave the screen saver and OLED panel care enabled. If the entry is missing, consult your model’s guide before changing any other idle-screen options. To restore the ads, turn this same switch on. [LG webOS 24 guide](https://kr.eguide.lgappstv.com/manual/w24_mr4/w24_cis07/eng.html) · [LG webOS 25 guide](https://kr.eguide.lgappstv.com/manual/w25/w25_br05/enga.html) · [LG webOS 26 guide](https://kr.eguide.lgappstv.com/manual/w26_tv/w26_eu02/eng.html)

<a id="live-promotions"></a>

## Promotions while watching, LG streams and promotional videos

If a banner appears only on certain broadcast channels, check whether it identifies the broadcaster or its interactive TV service. In markets with **HbbTV**, LG describes an option under **Channels → HbbTV** on some sets. Switching it off can also remove broadcaster features such as catch-up or the interactive programme page. Turn it back on if you use those features. For viewing-based LG suggestions, review [Live Plus and viewing consent](#viewing). [LG’s guide to identifying broadcast promotions](https://www.lg.com/it/supporto/supporto-prodotto/risoluzione-anomalie/help-library/cs-CT52001071-20153387508381/)

On some webOS 24/25 sets, **General → System → Additional Settings** includes **Live Promotion** alongside Live Plus. On webOS 26 check **System → Additional Settings**. If you use Live Plus, turn **Live Promotion** off to remove ads within it. If Live Plus is already off, leave it off. [LG webOS 24 guide](https://kr.eguide.lgappstv.com/manual/w24_mr4/w24_aja26/eng.html) · [LG webOS 26 guide](https://kr.eguide.lgappstv.com/manual/w26_tv/w26_tw04/engb.html)

CYTV’s Debloat list also includes **LG promotional streams** and **webOS promotional video**. We could not verify a public menu path to either of these individual settings. If the installer reports that a change was refused or could not be verified, check your model’s manual and leave the result unconfirmed if it gives no matching switch. Disabling LG Channels entirely would also remove access to its channels.

<a id="tips"></a>

## Smart Tips and recommendation notifications

On webOS 25, open **General → AI Service → AI Recommendation**. Turn off **Smart Tips** or **Smart Tips in Settings** for the surface where the tips appear. Review any separate content recommendation messages there. If your model groups recommendations under **LG AI Settings**, open that group and disable the suggestions you do not want. Restore each option individually if you miss its hints. [LG webOS 25 guide](https://kr.eguide.lgappstv.com/manual/w25/w25_u31/enga.html) · [CleanYourTV’s LG guide](https://cleanyour.tv/not-android#lg-2026)

For pop-ups from a particular app, open **Notifications** on LG Home. On supported webOS 26 sets, open **Notification Settings** and turn off that app. LG says doing this also clears messages already received from that app. Enabling it again allows future messages. [LG notifications guide](https://kr.eguide.lgappstv.com/manual/w26_tv/w26_mx02/enga.html)

<a id="sports"></a>

## Score and match alerts

Open **Sports Alert** (or the **Sports** card) on LG Home. Select a followed team or player and change its notification preferences, or remove it from favourites. If the app offers a single alert switch, turn it off to silence all of its match updates. Check the active LG profile if alerts return after someone switches accounts. To restore, select the team and the alerts again. [LG’s Sports Alerts walkthrough](https://www.lg.com/us/simroom/tvs/user-guide/2024/sports-alerts/) · [LG on alerts and profiles](https://www.lg.com/us/newsroom/media-entertainment/lg-begins-us-rollout-of-2023-oled-tv-lineup)

<a id="log-uploads"></a>

## Automatic debug and fault log uploads

If LG asks to send diagnostics, read the prompt and decline if you do not want to share them. We have no verified remote-menu path that sets both LG’s automatic debug-log and fault-log upload preferences across models. Declining one report establishes only your choice for that prompt. A CYTV result of **unknown**, **unavailable** or **denied** leaves the corresponding setting unconfirmed. The installer’s **Save diagnostic report** action is a separate, user-initiated export. [CYTV network and local data](CYTV-NETWORK.md) · [Diagnostic report guide](FEEDBACK.md)

## Check and undo

Reopen each changed setting and confirm its saved value. On firmware that rejects a change, note the model, webOS version and the choice shown on the TV. Check again after a major TV update or a fresh agreement prompt. If an app, voice feature or alert disappears, restore the individual agreement or switch in the same menu. For network filtering, follow the separate rollback instructions in the [DNS guide](PRIVACY-DNS.md).
