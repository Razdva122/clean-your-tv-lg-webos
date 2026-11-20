// Run only in the offline firmware harness. Service boundaries are modeled.
import QtQuick 2.4
import "../runtime/embedded-home.js" as Embedded

Item {
    id: probe
    property var stock
    property var attachment
    property var leaseReply
    property bool ran: false
    property int sends: 0
    property int lgDown: 0
    property int lgUp: 0

    function mark(name) { Qt.createComponent("file:///tmp/probe-markers/" + name + ".qml") }
    function later(milliseconds, callback) {
        var timer = timers.createObject(probe, { interval: milliseconds })
        timer.triggered.connect(function () {
            try { callback() } finally { timer.destroy() }
        })
        timer.start()
    }
    // Laboratory HTTP bridge models LS2/guardian delivery only. The Python
    // peer runs the real lifecycle watch() and proves SIGKILL plus pipe EOF.
    function request(path, callback) {
        var xhr = new XMLHttpRequest()
        xhr.onreadystatechange = function () {
            if (xhr.readyState === XMLHttpRequest.DONE) {
                if (xhr.status !== 200) { mark("bridge-failed"); return }
                callback(JSON.parse(xhr.responseText))
            }
        }
        xhr.open("GET", "http://127.0.0.1:34917" + path)
        xhr.send()
    }
    function subscribe(service, method, payload, callback) {
        var subscription = JSON.parse(payload)
        if (service !== "com.webos.cleanyourtv.root.lease" || method !== "/c1Lease" ||
                subscription.subscribe !== true || subscription.adapter !== "embedded-qml-v1") {
            mark("subscription-invalid")
            return
        }
        leaseReply = callback
        mark("tagged-subscription")
        request("/lease?adapter=" + subscription.adapter, function (reply) {
            callback(reply)
            verifyActive()
        })
    }
    function send(service, method, payload, callback) {
        if (service !== "com.webos.cleanyourtv.root.lease" || method !== "/c1Home" ||
                JSON.parse(payload).token !== "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa") {
            mark("home-request-invalid")
            return
        }
        sends++
        request("/home?token=" + JSON.parse(payload).token, function (reply) {
            callback(reply)
            request("/kill", function (killed) {
                if (!killed.returnValue) { mark("kill-failed"); return }
                mark("controller-sigkill-eof")
                request("/lease?adapter=embedded-qml-v1", function (dead) {
                    leaseReply(dead)
                    verifyFallback()
                })
            })
        })
    }
    function pair() {
        var filter = stock.ysm.keyFilter
        var down = filter.handleKeyPressed(Qt.Key_Super_L, false)
        var up = filter.handleKeyReleased(Qt.Key_Super_L, false)
        return down && up
    }
    function inspect() {
        if (ran || !stock || !stock.ysm) return
        ran = true
        var ysm = stock.ysm
        attachment = Embedded.attach(ysm, { later: probe.later, subscribe: probe.subscribe, send: probe.send })
        if (!attachment || !leaseReply) { mark("attach-failed"); return }
        mark("adapter-attached")
        ysm.smartTvReady = true
        ysm.keyFilter.homePressed.connect(function () { lgDown++ })
        ysm.keyFilter.homeReleased.connect(function () { lgUp++ })
    }
    function verifyActive() {
        var ysm = stock.ysm
        if (!pair() || sends !== 1 || lgDown !== 0 || lgUp !== 0 || ysm.state !== "hidden") {
            mark("intercept-failed")
            return
        }
        mark("home-intercepted")
    }
    function verifyFallback() {
        var ysm = stock.ysm
        if (!pair() || sends !== 1 || lgDown !== 1 || lgUp !== 1) {
            mark("fallback-failed")
            return
        }
        mark("stock-pair-delivered")
        later(500, function () {
            mark(ysm.state === "visible" ? "stock-home-visible" : "stock-home-hidden")
        })
    }
    Component.onCompleted: {
        var main = Qt.createComponent("qrc:///main.qml")
        if (main.status !== Component.Ready) { mark("stock-load-failed"); return }
        stock = main.createObject(null)
        inspect()
    }
    Connections {
        target: probe.stock
        ignoreUnknownSignals: true
        onYsmChanged: probe.inspect()
    }
    Timer {
        running: true
        interval: 1800
        onTriggered: probe.inspect()
    }
    Component { id: timers; Timer { repeat: false } }
}
