import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ApplicationWindow {
    id: settingsWindow
    objectName: "settingsWindow"
    title: "GPT-Niang Settings"
    width: 500
    height: 610
    minimumWidth: 420
    minimumHeight: 480
    visible: false
    color: "#f5f7fc"

    ScrollView {
        anchors.fill: parent
        anchors.margins: 24
        contentWidth: availableWidth
        clip: true
        ColumnLayout {
            width: parent.width
            spacing: 14
            Label { text: "GPT-Niang · Linux"; color: "#26354b"; font.pixelSize: 24; font.bold: true }
            Label { text: "拖动角色移动 · 单击查看额度 · 右键打开菜单"; color: "#5c6b80"; wrapMode: Text.Wrap; Layout.fillWidth: true }
            Label { text: "角色尺寸  " + Math.round(preferences.scale * 100) + "%"; color: "#334155" }
            Slider {
                id: sizeSlider
                Layout.fillWidth: true
                from: 0.6; to: 2.5; stepSize: 0.01
                value: preferences.scale
                onPressedChanged: if (!pressed) preferences.setScale(value)
                onMoved: if (!pressed) preferences.setScale(value)
            }
            RowLayout {
                Repeater {
                    model: [0.8, 1.0, 1.4]
                    Button { required property real modelData; text: Math.round(modelData * 100) + "%"; onClicked: preferences.setScale(modelData) }
                }
            }
            CheckBox { text: "启用已导入的 Coopanion 分层模型"; checked: preferences.modelEnabled; onToggled: preferences.setModelEnabled(checked) }
            CheckBox { text: "显示基本语录"; checked: preferences.quotesEnabled; onToggled: preferences.setQuotesEnabled(checked) }
            Rectangle { Layout.fillWidth: true; height: 1; color: "#dce3ed" }
            Label { text: "KDE 窗口管理"; color: "#334155"; font.bold: true }
            Label { text: windowBackend.placementStatus; color: "#64748b"; wrapMode: Text.Wrap; Layout.fillWidth: true }
            Label { text: "置顶请通过 KDE 窗口规则配置，默认关闭。尺寸由应用保存。"; color: "#64748b"; wrapMode: Text.Wrap; Layout.fillWidth: true }
            Button { text: "打开 KDE 窗口规则…"; onClicked: preferences.openKdeRules() }
            Rectangle { Layout.fillWidth: true; height: 1; color: "#dce3ed" }
            Label { text: "额度运行环境"; color: "#334155"; font.bold: true }
            Label { text: "Node.js 可执行文件"; color: "#64748b"; font.pixelSize: 12 }
            TextField { id: nodePath; text: preferences.nodePath; selectByMouse: true; placeholderText: "自动检测，或输入绝对路径"; Layout.fillWidth: true }
            Label { text: "Codex 可执行文件"; color: "#64748b"; font.pixelSize: 12 }
            TextField { id: codexPath; text: preferences.codexPath; selectByMouse: true; placeholderText: "自动检测，或输入绝对路径"; Layout.fillWidth: true }
            RowLayout {
                Button { text: "自动检测"; onClicked: preferences.detectPaths() }
                Button { text: "保存并刷新"; onClicked: { preferences.setPaths(nodePath.text, codexPath.text); quota.manualRefresh() } }
            }
            Label { text: preferences.notice; textFormat: Text.PlainText; color: "#6a7284"; wrapMode: Text.Wrap; Layout.fillWidth: true }
            Label { text: "Linux " + preferences.version + " · QPA: " + windowBackend.platform + "\n额度仅保存在内存；登录由 Codex 维护。"; color: "#64748b"; font.pixelSize: 11; Layout.fillWidth: true; wrapMode: Text.Wrap }
            Button { text: "退出桌宠"; onClicked: Qt.quit() }
        }
    }
}
