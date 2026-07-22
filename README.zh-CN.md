# Sprite Pet Skill

[English](README.md) | 简体中文

把一张角色图变成精致、会动、能互动的桌面宠物。

这个仓库不只提供提示词，还包含动作设计、精灵图处理、质量校验、Electron 运行时、打包和启动验证的完整工作流。

## 它解决什么

生成桌宠最难的通常不是“让角色动起来”，而是让所有动作看起来仍然是同一个角色，并且在桌面上稳定运行。Sprite Pet Skill 针对这些常见问题提供了可复用的处理与验证：

- Idle、Walk、Run 切换时体型忽大忽小；
- 睡觉、受伤、死亡或蜷缩动作出现身份漂移；
- 透明图里残留尾巴碎片、网格线或裁切边缘；
- 宠物在鼠标附近反复扑跳和抖动；
- 长按逗宠时切头旋转，造成脖子断裂；
- 只生成素材，却没有真正打包并运行桌宠。

## 功能

- 五种运动骨架：`biped`、`quadruped`、`serpent`、`flyer`、`blob`；
- 基于身份锚点和姿势图生成独立的 4×2 八帧动作表；
- 洋红背景抠除、去色溢、落地对齐、中心校正与透明图导出；
- 身份一致性、重复帧、透明碎片、边缘安全区和循环质量检查；
- Idle、Walk、Run 跨动作比例审计及 `displayScale` 校准；
- 完整八方向长按注视方案，避免平面图片“切头旋转”；
- 带透明点击穿透、菜单、多屏约束和防抖追逐逻辑的 Electron 模板；
- macOS、Windows 结构化打包以及当前系统启动验证。

## 安装

把仓库克隆到你的 AI Agent 能发现 `SKILL.md` 的技能目录中：

```bash
git clone https://github.com/promptwhisper/sprite-pet-skill.git \
  <skills-directory>/sprite-pet-skill
```

安装图像处理依赖：

```bash
python3 -m pip install -r \
  <skills-directory>/sprite-pet-skill/scripts/requirements.txt
```

不同 Agent 的技能目录和调用方式可能不同。如果宿主支持显式技能调用，可以使用 `$sprite-pet-skill`；否则直接描述桌宠制作任务即可。

核心工作流只依赖 `SKILL.md`、`scripts/`、`references/` 和 `assets/`，不绑定特定 Agent。`agents/openai.yaml` 只是可选的宿主界面元数据，不影响其他环境使用。

## 使用示例

```text
使用 $sprite-pet-skill，把这张猫咪图片做成会待机、行走、奔跑和追逐鼠标的桌宠，完成后直接打包并运行。
```

```text
修复这个桌宠：Idle 比走路大、跑步比走路小，而且鼠标停住后宠物会反复扑跳。
```

```text
长按桌宠时让它固定在原地，头部自然朝鼠标的八个方向转动；不要切下头部旋转。
```

```text
使用 $sprite-pet-skill，把这张幼龙图片做成比例一致的桌宠，包含待机、走路、跑步、追逐和长按八方向注视，完成后打包并运行。
```

## 工作流

```text
角色图片或角色概念
        ↓
身份锚点 + 身体类型选择
        ↓
动作姿势图 + 独立八帧动作表
        ↓
透明化、对齐、比例归一和碎片处理
        ↓
跨动作审计 + 人工播放检查
        ↓
Electron 桌宠运行时
        ↓
打包、验证并启动
```

详细执行规范位于 [SKILL.md](SKILL.md)。交互模型见 [pointer-interactions.md](references/pointer-interactions.md)，Electron 行为约束见 [electron-runtime.md](references/electron-runtime.md)。

## 内置工具

| 工具 | 用途 |
| --- | --- |
| `prepare_character_anchor.py` | 将角色图规范为稳定的身份锚点 |
| `generate_pose_guides.py` | 为不同身体类型和动作生成姿势图 |
| `process_sprite_sheets.py` | 处理、对齐并导出动作帧和 manifest |
| `validate_animations.py` | 检测重复帧、裁切、碎片和比例漂移 |
| `audit_sprite_set.py` | 审计跨动作体型并写入显示比例 |
| `export_sprite_bundle.py` | 导出帧、网格图、条带图、ZIP 和提示词 |
| `scaffold_electron_pet.py` | 创建透明 Electron 桌宠工程 |
| `launch_desktop_pet.py` | 启动当前系统最新的可用构建 |

查看命令参数：

```bash
python3 scripts/<tool-name>.py --help
```

## 设计原则

1. 角色身份优先于动作夸张程度。
2. 相同画布尺寸不等于相同视觉体型，必须检查真实轮廓和视觉质量。
3. 只自动清理极小且明确的透明碎片；可能属于尾巴、耳朵、翅膀或肢体的部分必须重新生成。
4. 平面 PNG 的方向跟随使用完整角色帧；只有真正带遮挡、蒙版和枢轴的骨骼素材才允许单独旋转头部。
5. 生成、验证、打包和启动属于同一个交付流程。

## 运行要求

- Python 3 和 Pillow；
- 可接收参考图的图像生成能力；
- 构建 Electron 桌面运行时需要 Node.js 和 npm；
- Electron 模板依赖版本记录在 `assets/electron-template/package.json`。

## 来源说明

精灵动画方法基于 MIT 许可的 [promptwhisper/sprite-generator](https://github.com/promptwhisper/sprite-generator) 改编。具体来源、固定提交和复用范围见 [provenance.md](references/provenance.md)，上游许可见 [UPSTREAM_LICENSE.txt](references/UPSTREAM_LICENSE.txt)。
