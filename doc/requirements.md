# MidView 需求文档

## 1. 项目概述

基于 PySide6 的桌面应用，在圆形晶圆图上交互式可视化缺陷检测数据。前后端分离，Google 命名规范。

## 2. 数据模型

`backend/models.py` 中 6 个 dataclass：`Defect`（54 字段）、`Event`（47 字段，含链表指针索引）、`PacketRawMeta`（10 字段）、`PacketImage`（head/data/footer）、`PacketMeta`（12 字段）、`ImageMeta`（12 字段 + PacketMeta 列表）。

## 3. 数据加载

- **Load Data** 按钮 → 选择文件夹，加载 `defects.csv`。`events.csv` 和 `packet_raw_meta.csv` 为懒加载
- **events.csv** — 右键 → "View Events" 时懒加载
- **packet_raw_meta.csv** — "View All Spiral" 时懒加载
- **img_and_packet_meta.csv** — 双层格式（ImageMeta 头部行 + PacketMeta 子行），按需加载
- Event 指针字段（`next`、`parent`、`prev` 等）为 `event_array` 下标，-1 表示空
- 加载模块：`defect_loader`、`event_loader`、`packet_raw_meta_loader`、`image_meta_loader`、`packet8M_loader`

## 4. 坐标系

| 参数 | 范围 | 说明 |
| --- | --- | --- |
| 原点 | (0, 0) | 场景坐标原点 |
| 半径 | 150,000 μm | 黑色圆圈，无填充 |
| wenc | 0 ~ 262,144 | 顺时针，0° 为 3 点钟方向 |
| xenc | 0 ~ 187,500 | 外圈 → 圆心；xenc=2400 → r≈150,000 |
| 转换 | `θ = 2π·wenc/262144`, `r = 150000·(187500−xenc)/(187500−2400)` | `x = r·cos(θ)`, `y = r·sin(θ)` |

## 5. Defect 可视化

- 位置：`wenc_xenc_to_xy(dft.w_encoder, dft.x_encoder)`
- 大小：屏幕恒定 ~2px（`ItemIgnoresTransformations`），悬浮 4px，选中 6px
- 颜色：正常红色 `#dc3545`，悬浮橙红，选中蓝色 `#2563a0`
- 左键自动选中最近 defect（自适应 25px 屏幕距离）；再次点击取消选中
- 偏离原点时显示指向 (0,0) 的箭头指示器

## 6. Event 区域

- 右键 defect → "View Events"：加载 `events.csv`，沿 `next` 指针链遍历至 -1
- 两层多边形：
  1. Defect 自身区域：红色虚线 `#dc3545`，无填充
  2. Event 链区域：蓝色边框 `#5ba0d0`，半透明填充，可点击
- 四角多边形：`(xenc_outer,wenc_left)`、`(xenc_outer,wenc_right)`、`(xenc_inner,wenc_right)`、`(xenc_inner,wenc_left)`
- 同一 defect 不重复绘制；"Clear All Events" 清除全部

## 7. 螺旋轨迹

- 逐行绘制 `(xenc_outer, wenc_left)` → `(xenc_inner, wenc_right)` 线段
- 首尾相连；浅灰 `#c0c0c0`，cosmetic pen；绿色起点标记；packet_id 标签
- 绘制过程中显示进度对话框

## 8. Packet8M 查看器

- 解析 8,388,608 字节 `.tt` 二进制文件（64B 头，uint16 2048×2048 + 3 编码器列，8B 尾）
- 对话框：QGraphicsView、直方图、滑块（Min/Max 百分位、Contrast、Brightness）、Auto/Reset/Draw 按钮
- Draw 按钮将转置后的 packet 图像投影到晶圆画布的编码器坐标位置
- 对话框内叠加 Event 区域（蓝色虚线，可点击）
- 右键拖拽框选缩放、滚轮缩放、悬浮像素值查看
- 相邻扫描区域以黄色虚线显示

## 9. Defect 图像查看器

- 对含有 `img_and_packet_meta.csv` 元数据的 defect 打开
- ImageMeta + PacketMeta 表格；可浏览 `.png` 图像，像素值读取，8/16-bit 切换

## 10. 面板

### DetailPanel（右侧栏）

- 搜索：字段下拉（defect_id、img_id、cluster_number 等）+ 输入值 → 画布居中并选中
- 选中 defect 时显示全部字段的紧凑属性列表

### EventInfoPanel（右侧栏，DetailPanel 下方）

- 标题栏 `#b8cfe0`，内容区 `#e8f0f8`；点击 event 区域时显示全部 Event 字段
- × 按钮关闭；点击 defect 时自动隐藏

## 11. 坐标对比

- 计算 `wenc_xenc_to_xy()` 结果与存储 `(x, y)` 之间的欧氏距离
- Matplotlib 散点图，含 min/max/mean/std 统计

## 12. 画布交互

| 操作 | 行为 |
| --- | --- |
| 左键点击 defect 附近 | 选中最近 defect（自适应阈值） |
| 左键点击同一 defect | 取消选中 |
| 右键点击 defect 附近 | 选中，弹出右键菜单 |
| 右键点击空白 | Clear All Events / Clear All Packet Images |
| 右键拖拽 | 框选缩放 |
| 滚轮 | 以光标为锚点缩放 ×1.15 |
| Fit View | 拟合圆圈至视口 |

## 13. UI 主题

柔和暖色系：底色 `#f5f4f1`，组件 `#eeedea`，边框 `#d8d6d2`，强调色 `#2563a0`。统一定义于 `frontend/theme.py` 的 `LIGHT_THEME`。

## 14. 项目结构

```text
MidView/
├── main.py
├── build.py
├── backend/
│   ├── models.py
│   └── data_load/
│       ├── _helpers.py
│       ├── defect_loader.py
│       ├── event_loader.py
│       ├── packet_raw_meta_loader.py
│       ├── image_meta_loader.py
│       └── packet8M_loader.py
├── frontend/
│   ├── main_window.py
│   ├── circular_view.py
│   ├── detail_panel.py
│   ├── coordinate_utils.py
│   └── theme.py
└── data/
    └── <数据集文件夹>/
```
