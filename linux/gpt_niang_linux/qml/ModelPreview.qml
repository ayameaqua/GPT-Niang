import QtQuick
import QtQuick.Window
import QtQuick.Controls
import QtQuick.Layouts
import GPTNiang.Model 1.0

ApplicationWindow {
    id: preview
    objectName: "modelPreview"
    title: "GPT-Niang Model Preview"
    width: 960; height: 760
    minimumWidth: 820; minimumHeight: 650
    color: "#f0edf6"
    property var controller

    RowLayout {
        anchors.fill: parent; anchors.margins: 20; spacing: 20
        ColumnLayout {
            Layout.preferredWidth: 430; Layout.fillHeight: true
            Label { text: "龙娘 · 模型预览"; font.pixelSize: 25; font.bold: true; color: "#39304e" }
            Label { text: controller.status; wrapMode: Text.Wrap; Layout.fillWidth: true; color: "#6d6380" }
            Rectangle {
                Layout.fillWidth: true; Layout.fillHeight: true
                color: "#dad5e5"; radius: 14
                DragonModel {
                    id: display
                    anchors.centerIn: parent
                    width: Math.min(parent.width, parent.height); height: width
                    follow: controller
                    active: preview.visible && controller.available
                    visible: active
                }
            }
            Label {
                text: "当前动作：" + (controller.motion || "待机") + " · 朝向：" + controller.orientation
                color: "#544467"; Layout.fillWidth: true
            }
            RowLayout {
                Button { text: controller.paused ? "继续" : "暂停"; onClicked: controller.setPaused(!controller.paused) }
                Button { text: "取消 / 复位"; onClicked: controller.reset() }
                CheckBox { text: "连接点"; checked: controller.debug; onToggled: controller.setDebug(checked) }
            }
            RowLayout {
                Label { text: "速度" }
                Slider { from: 0.1; to: 2; value: 1; Layout.fillWidth: true; onMoved: controller.setSpeed(value) }
                Label { text: controller.speed.toFixed(1) + "×" }
            }
            RowLayout {
                CheckBox { text: "说话口型"; checked: controller.speaking; onToggled: controller.setSpeaking(checked) }
                CheckBox { text: "倾听"; checked: controller.listening; onToggled: controller.setListening(checked) }
            }
            Label {
                text: "仅在画布内演示走跑和抛落。真实窗口位置仍由 KWin 管理。\n未完成绑定的视角会标注，不能当作已完成模型。"
                font.pixelSize: 11; wrapMode: Text.Wrap; Layout.fillWidth: true; color: "#6d6380"
            }
        }
        ScrollView {
            Layout.fillWidth: true; Layout.fillHeight: true; clip: true; contentWidth: availableWidth
            ColumnLayout {
                width: parent.width; spacing: 12
                Label { text: "朝向"; font.bold: true }
                Flow {
                    Layout.fillWidth: true; spacing: 6
                    Repeater {
                        model: controller.views
                        Button {
                            required property var modelData
                            text: modelData.name + (modelData.ready ? "" : " · 待绑定")
                            enabled: modelData.ready
                            highlighted: controller.orientation === modelData.id
                            onClicked: controller.setView(modelData.id)
                        }
                    }
                }
                Label { text: "19 种基线表情"; font.bold: true }
                Flow {
                    Layout.fillWidth: true; spacing: 6
                    Repeater {
                        model: controller.expressions
                        Button {
                            required property var modelData
                            text: modelData.name
                            enabled: controller.available
                            highlighted: controller.expression === modelData.id
                            onClicked: controller.setExpression(modelData.id)
                        }
                    }
                }
                Label { text: "18 种基线动作 + 新增手势 / 互动"; font.bold: true; wrapMode: Text.Wrap; Layout.fillWidth: true }
                Flow {
                    Layout.fillWidth: true; spacing: 6
                    Repeater {
                        model: controller.motions
                        Button {
                            required property var modelData
                            text: modelData.name + (modelData.ready ? "" : " · 待绑定")
                            enabled: controller.available && modelData.ready
                            highlighted: controller.motion === modelData.id
                            onClicked: controller.play(modelData.id)
                        }
                    }
                }
            }
        }
    }
}
