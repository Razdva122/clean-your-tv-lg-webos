import QtQuick 2.4
import WebOSServices 1.0
import "embedded-home.js" as Embedded

Item {
    id: wrapper
    property var attachment: null
    property var callbacks: ({})
    property bool adapterReady: attachment !== null

    function later(milliseconds, callback) {
        var timer = oneShot.createObject(wrapper, { interval: milliseconds })
        if (!timer) throw new Error("Embedded Home timer unavailable")
        timer.triggered.connect(function () {
            try { callback() } finally { timer.destroy() }
        })
        timer.start()
    }

    function request(service, method, payload, callback) {
        if (service !== "com.webos.cleanyourtv.root.lease" ||
                (method !== "/c1Lease" && method !== "/c1Home"))
            throw new Error("Unexpected embedded Home request")
        callbacks[method] = callback
        lease.call("luna://" + service, method, payload)
    }

    function attach() {
        if (attachment || !original.item || !original.item.ysm) return
        attachment = Embedded.attach(original.item.ysm, {
            later: wrapper.later,
            subscribe: wrapper.request,
            send: wrapper.request
        })
    }

    Loader {
        id: original
        anchors.fill: parent
        source: "qrc:///main.qml"
        onLoaded: wrapper.attach()
    }

    Connections {
        target: original.item
        ignoreUnknownSignals: true
        onYsmChanged: wrapper.attach()
    }

    Component {
        id: oneShot
        Timer { repeat: false }
    }

    Service {
        id: lease
        appId: "com.webos.surfacemanager"
        onResponse: {
            var callback = wrapper.callbacks[method]
            if (typeof callback !== "function") return
            if (method === "/c1Home") delete wrapper.callbacks[method]
            callback(payload)
        }
    }

    Component.onDestruction: if (attachment) attachment.retire()
}
