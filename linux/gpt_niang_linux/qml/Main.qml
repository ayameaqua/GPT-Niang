import QtQuick
import QtQuick.Window
import QtQuick.Controls
import QtQuick.Layouts
import GPTNiang.Model 1.0

Window {
    id: petWindow
    objectName: "petWindow"
    title: "GPT-Niang Pet"
    visible: true
    color: "transparent"
    flags: Qt.Window | Qt.FramelessWindowHint | Qt.WindowDoesNotAcceptFocus
    property bool previewVisible: false
    readonly property bool modelActive: preferences.modelEnabled && dragon.available
    readonly property real petHeight: (modelActive ? 320 : 230) * preferences.scale
    readonly property int canvasWidth: Math.ceil(Math.max(364, petHeight * (modelActive ? 1 : windowBackend.imageAspect) + 24))
    readonly property int canvasHeight: Math.ceil(350 + petHeight + 16)
    width: canvasWidth
    height: canvasHeight
    minimumWidth: canvasWidth
    maximumWidth: canvasWidth
    minimumHeight: canvasHeight
    maximumHeight: canvasHeight
    property bool bubbleVisible: false

    function updateInputMask() {
        windowBackend.updateMask(character.x, character.y, character.width, character.height,
                                 bubbleVisible, bubble.x, bubble.y, bubble.width, bubble.height)
    }
    onWidthChanged: maskTimer.restart()
    onHeightChanged: maskTimer.restart()
    onBubbleVisibleChanged: maskTimer.restart()
    Component.onCompleted: maskTimer.start()
    Timer { id: maskTimer; interval: 0; onTriggered: petWindow.updateInputMask() }

    Connections {
        target: windowBackend
        function onDragStarted() { if (petWindow.modelActive) dragon.play("carried") }
        function onDragEnded() { if (petWindow.modelActive) dragon.play("land") }
        function onPetClicked() {
            if (petWindow.modelActive) dragon.play("poke")
            petWindow.bubbleVisible = !petWindow.bubbleVisible
            if (petWindow.bubbleVisible) {
                quota.ensureFresh()
                preferences.nextQuote()
            }
        }
    }
    Connections {
        target: preferences
        function onModelPreviewRequested() {
            petWindow.previewVisible = true
            modelPreview.raise()
            modelPreview.requestActivate()
        }
        function onSettingsRequested() {
            settingsWindow.show()
            settingsWindow.raise()
            settingsWindow.requestActivate()
        }
        function onChanged() { maskTimer.restart() }
    }

    Rectangle {
        id: bubble
        objectName: "quotaBubble"
        visible: petWindow.bubbleVisible
        x: Math.round((petWindow.width - width) / 2)
        y: 8
        width: 348
        height: 330
        radius: 12
        color: "#f5f7fc"
        border.color: "#c6cfdf"
        border.width: 1

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: 16
            spacing: 8
            RowLayout {
                Layout.fillWidth: true
                Label { text: "Codex 额度"; color: "#1e293b"; font.pixelSize: 18; font.bold: true; Layout.fillWidth: true }
                Label { text: quota.planLabel; color: "#475569"; font.pixelSize: 12 }
                ToolButton { text: "×"; implicitWidth: 28; implicitHeight: 28; onClicked: petWindow.bubbleVisible = false; Accessible.name: "关闭气泡" }
            }
            Label {
                Layout.fillWidth: true
                text: quota.status
                color: quota.stale ? "#9a5700" : "#536079"
                font.pixelSize: 12
                wrapMode: Text.Wrap
                maximumLineCount: 3
                elide: Text.ElideRight
                textFormat: Text.PlainText
            }
            ScrollView {
                Layout.fillWidth: true
                Layout.fillHeight: true
                clip: true
                contentWidth: availableWidth
                ColumnLayout {
                    width: parent.width
                    spacing: 10
                    Label {
                        visible: quota.windows.length === 0
                        text: quota.busy ? "正在向本机 Codex 读取…" : "暂无可显示额度\n请确认 Codex 使用 ChatGPT 账户登录。"
                        Layout.fillWidth: true
                        wrapMode: Text.Wrap
                        color: "#64748b"
                        font.pixelSize: 13
                    }
                    Repeater {
                        model: quota.windows
                        delegate: ColumnLayout {
                            required property var modelData
                            Layout.fillWidth: true
                            spacing: 4
                            RowLayout {
                                Layout.fillWidth: true
                                Label { text: modelData.label; textFormat: Text.PlainText; font.pixelSize: 13; color: "#334155"; Layout.fillWidth: true }
                                Label { text: "剩余 " + modelData.remainingLabel; font.pixelSize: 13; font.bold: true; color: "#254a70" }
                            }
                            ProgressBar {
                                from: 0; to: 100; value: modelData.remaining
                                Layout.fillWidth: true
                                implicitHeight: 7
                                background: Rectangle { implicitHeight: 7; color: "#dce4f0"; radius: 3 }
                                contentItem: Item {
                                    Rectangle { width: parent.width * parent.parent.visualPosition; height: parent.height; radius: 3; color: modelData.freshness === "fresh" ? "#738fca" : "#b79462" }
                                }
                            }
                            Label {
                                text: (modelData.freshness === "expired" ? "已到重置时间，请刷新 · " : modelData.freshness === "stale" ? "旧数据 · " : "") + "重置 " + modelData.resetLabel
                                color: "#64748b"; font.pixelSize: 10; Layout.fillWidth: true; wrapMode: Text.Wrap
                            }
                        }
                    }
                }
            }
            Label {
                text: "成功数据 " + quota.updatedLabel + "\n最近尝试 " + quota.attemptedLabel
                color: "#64748b"; font.pixelSize: 10; Layout.fillWidth: true; wrapMode: Text.Wrap
            }
            RowLayout {
                Layout.fillWidth: true
                Label {
                    text: preferences.quotesEnabled ? preferences.quote : ""
                    textFormat: Text.PlainText
                    color: "#55617a"; font.pixelSize: 11; Layout.fillWidth: true; wrapMode: Text.Wrap
                    maximumLineCount: 2; elide: Text.ElideRight
                }
                Button { text: quota.busy ? "刷新中…" : "刷新"; enabled: !quota.busy; onClicked: quota.manualRefresh(); implicitHeight: 30 }
            }
        }
    }

    Item {
        id: character
        objectName: "character"
        height: petWindow.petHeight
        width: height * (petWindow.modelActive ? 1 : windowBackend.imageAspect)
        x: Math.round((petWindow.width - width) / 2)
        y: 350
        onWidthChanged: maskTimer.restart()
        onHeightChanged: maskTimer.restart()
        Image {
            anchors.fill: parent
            visible: !petWindow.modelActive
            source: preferences.characterUrl
            sourceSize.height: Math.ceil(height * petWindow.Screen.devicePixelRatio)
            fillMode: Image.PreserveAspectFit
            smooth: true
            opacity: windowBackend.pressed ? 0.88 : 1.0
        }
        DragonModel {
            id: dragon
            objectName: "dragonRenderer"
            anchors.fill: parent
            active: petWindow.modelActive
            visible: active
        }
        MouseArea {
            anchors.fill: parent
            acceptedButtons: Qt.LeftButton | Qt.RightButton
            preventStealing: true
            hoverEnabled: true
            onPressed: function(mouse) {
                if (mouse.button === Qt.RightButton) {
                    windowBackend.cancelPointer()
                    contextMenu.popup()
                } else windowBackend.pointerPress(mouse.x, mouse.y)
            }
            onPositionChanged: function(mouse) {
                if (petWindow.modelActive) dragon.lookAt((mouse.x / width - 0.5) * 2, (mouse.y / height - 0.4) * 2)
                if (pressedButtons & Qt.LeftButton) windowBackend.pointerMove(mouse.x, mouse.y)
            }
            onExited: dragon.lookAt(0, 0)
            onReleased: function(mouse) { if (mouse.button === Qt.LeftButton) windowBackend.pointerRelease() }
            onCanceled: windowBackend.cancelPointer()
            onDoubleClicked: if (petWindow.modelActive) dragon.play("pet")
        }
    }

    ModelPreview {
        id: modelPreview
        controller: dragon
        visible: petWindow.previewVisible
        onClosing: petWindow.previewVisible = false
    }

    Menu {
        id: contextMenu
        popupType: Popup.Window
        MenuItem { text: petWindow.bubbleVisible ? "收起额度" : "查看额度"; onTriggered: { petWindow.bubbleVisible = !petWindow.bubbleVisible; if (petWindow.bubbleVisible) quota.ensureFresh() } }
        MenuItem { text: "刷新额度"; enabled: !quota.busy; onTriggered: { petWindow.bubbleVisible = true; quota.manualRefresh() } }
        MenuItem { text: "换一句话"; onTriggered: { preferences.nextQuote(); petWindow.bubbleVisible = true } }
        MenuItem { text: "模型与动作预览…"; onTriggered: { petWindow.previewVisible = true; modelPreview.raise(); modelPreview.requestActivate() } }
        MenuSeparator {}
        Menu {
            title: "角色尺寸"
            MenuItem { text: "80%"; onTriggered: preferences.setScale(0.8) }
            MenuItem { text: "100%"; onTriggered: preferences.setScale(1.0) }
            MenuItem { text: "140%"; onTriggered: preferences.setScale(1.4) }
        }
        MenuItem { text: "设置…"; onTriggered: preferences.showSettings() }
        MenuSeparator {}
        MenuItem { text: "退出"; onTriggered: Qt.quit() }
    }

    SettingsWindow { id: settingsWindow }
}
