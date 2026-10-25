#!/bin/sh
# Read system toggles from settings.json and enforce them.
# Called by the root service at boot and after each toggle change.
SETTINGS="/media/developer/natxo/settings.json"
[ -f "$SETTINGS" ] || exit 0

# Parse JSON booleans without jq (busybox-only environment)
get() { sed -n "s/.*\"$1\" *: *\(true\|false\).*/\1/p" "$SETTINGS" | head -1; }

# --- eARC audio delay fix ---
# Adapted from zzeppieri/webos-custom-home: toggle the eArcSupport setting
# itself to force a real eARC protocol re-negotiation, rather than switching
# sound output. Only acts when output is already external_arc. Preserves the
# user's original eArcSupport value (ARC-only receivers stay on ARC).
if [ "$(get earcFix)" = "true" ]; then
    (sleep 15
     SOUND=$(luna-send -n 1 -f luna://com.webos.settingsservice/getSystemSettings '{"category":"sound","keys":["soundOutput","eArcSupport"]}' 2>/dev/null)
     OUTPUT=$(echo "$SOUND" | sed -n 's/.*"soundOutput" *: *"\([^"]*\)".*/\1/p')
     EARC=$(echo "$SOUND" | sed -n 's/.*"eArcSupport" *: *"\([^"]*\)".*/\1/p')
     if [ "$OUTPUT" = "external_arc" ]; then
         if [ "$EARC" = "on" ]; then FLIP="off"; else FLIP="on"; fi
         luna-send -n 1 -f luna://com.webos.settingsservice/setSystemSettings '{"category":"sound","settings":{"eArcSupport":"'"$FLIP"'"}}' 2>/dev/null
         sleep 2
         luna-send -n 1 -f luna://com.webos.settingsservice/setSystemSettings '{"category":"sound","settings":{"eArcSupport":"'"$EARC"'"}}' 2>/dev/null
     fi
    ) &
fi

# --- Block Bluetooth ---
if [ "$(get disableBluetooth)" = "true" ]; then
    luna-send -n 1 -f luna://com.webos.service.bluetooth2/adapter/setState '{"powered":false}' 2>/dev/null
else
    luna-send -n 1 -f luna://com.webos.service.bluetooth2/adapter/setState '{"powered":true}' 2>/dev/null
fi

# --- Block microphone ---
if [ "$(get disableMicrophone)" = "true" ]; then
    luna-send -n 1 -f luna://com.webos.service.audio/master/setMicMute '{"micMute":true}' 2>/dev/null
else
    luna-send -n 1 -f luna://com.webos.service.audio/master/setMicMute '{"micMute":false}' 2>/dev/null
fi
