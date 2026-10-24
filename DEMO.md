# SaltShield：三分钟 Demo

演示入口：https://evelynkatayose.github.io/saltshield/?demo=1

演示模式不读取或覆盖普通模式保存的预算、项目和容量。每次重新加载或点 Restart demo 都从默认情景开始。

## 1. 雪景开场（0:00–0:20）

**怎么点：** 打开带 ?demo=1 的演示入口。先在雪景上移动鼠标，拨动雪花。

**应当看到：** 固定从 $75,000、Central、Zone A、默认设备容量开始。不要一开始就讲算法。

> SaltShield helps neighboring towns plan winter equipment investments around a shared drinking-water source.

## 2. 展示雪、盐与水的联系（0:20–0:45）

**怎么点：** 点顶栏 The story。点 02 Salt → Add salt，再点 03 Water → Make a ripple。给盐粒几秒钟移动的时间。

**应当看到：** 看到盐粒、流水与涟漪。这里只解释问题，粒子不代表实测盐量或水质预测。

> The animation introduces the connection. Our decision model focuses on equipment purchases and where they can work.

## 3. 展示同一预算上限下的两种投资（0:45–1:15）

**怎么点：** 点固定顶栏 Explore the map。预算保持 $75,000。先点 Independent，再点 Shared budget。

**应当看到：** Independent：花费 $45,000，分配 74.66 km，模拟 Zone A 减盐 20.15 t。Shared：花费 $75,000，分配 124.57 km，模拟 60.68 t。必须解释两者实际支出不同。

> Both rules have the same total budget ceiling. The shared plan also buys more equipment, so we separately compare equal actual spending.

## 4. 核心演示：相同实际支出（1:15–1:45）

**怎么点：** 在地图右侧的预算滑块下面找到 Demo budgets，点 $45,000 快捷按钮。切换 Independent 和 Shared budget。拖动地图对比滑块，再展开 Town allocation & spending，把鼠标放到一个城镇上。

**应当看到：** 两种规则都花 $45,000。Independent：20.15 t、3 镇；Shared：34.35 t、2 镇。地图显示真实被分配的道路片区。

> At the same forty-five-thousand-dollar spending, the simulated pooled plan avoids more Zone A application, but funds only two towns.

## 5. 展示参与约束（1:45–2:10）

**怎么点：** 保持 $45,000，点顶栏 Open planner。Funding rule 从 Shared budget 改为 Shared · every town。

**应当看到：** 要求三镇都有项目后，模拟 Zone A 减盐量回到 20.15 t。再选回 Shared budget，恢复 34.35 t、2 镇。

> Requiring every town to participate changes the recommendation. The tool makes the efficiency and participation tradeoff visible.

## 6. 检查容量不确定性（2:10–2:35）

**怎么点：** 在 Road Coverage 页面向下找到 Reach check，点 Run reach check。浏览九种情景和项目选择频次。

**应当看到：** CAL 和 BRINE 的覆盖能力分别变化 ±25%，预算和价格保持不变。频次是情景计数，不是成功概率。

> We test nine assumed equipment-reach cases and show when the recommendation changes.

## 7. 导出并收尾（2:35–3:00）

**怎么点：** 回到当前面板上方，点 Download decision brief。说明也可以导出 linked plan JSON 和 assigned cells CSV。

**应当看到：** 简报包含当前 $45,000 方案、地图、参数、来源与已运行的容量检查。不要拿保存的 $75,000 示例简报替代这次的动态导出。

> The geography is measured. Costs, capacity and effect estimates are simulated. The next validation step is municipal salt logs, usable equipment capacity and vendor quotes.

## 临场处理

- 迷路时：固定顶栏可跳到 The story、Explore the map 或 Open planner。工作台左上角 SaltShield 返回雪景首页。
- 数字不对时：点 Restart demo。它回到 $75,000 的默认开场，不改你普通模式保存的参数。
- 演示卡顿时：点 Pause motion。真实预算与地图计算仍可使用。
- 预算拖不准时：用 Demo budgets 的 $75,000 / $45,000 快捷按钮。
- 问到数据时：在 Evidence 展示 GIS 来源、历史资助记录和明确标注的模拟参数。历史资助不是当前设备报价。

## 技术核心（被问到时）

The core combines measured GIS geometry, conservative dynamic programming for whole-road-cell coverage, and exhaustive equipment-portfolio search for the six-project pilot.
