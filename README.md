# G14 Pipeline — QXU6028 Virtual Lab 复现管道

G14 组（数据集 `regular_G14`）的完整分析管道：L1 正向模型、L2 零维逆问题、L3 二维逆问题。

## 一键复现

```bash
python reproduce.py            # 常规数据 -> outputs/results.json + 5 张图
python reproduce.py --check    # 内置验证检查
python reproduce.py blind      # 盲测数据 -> outputs/blind_results.json
```

要求：Python 3.10+（3.9 亦可用），依赖见 `requirements.txt`。

## 目录结构

```
g14_pipeline/
├── reproduce.py            # 一键管道（盲测时唯一允许改的是数据路径）
├── requirements.txt
├── data/regular_G14/       # 原始数据（勿改动）
├── src/
│   ├── common.py           # 常量与共享函数
│   ├── l1.py               # L1 正向载流子计数
│   ├── l2.py               # L2 零维逆问题 + bootstrap
│   └── l3.py               # L3 正则化重建
├── outputs/
│   ├── results.json        # 机器可读结果（QXU6028-results-v1 schema）
│   └── figures/            # 6 张图（L2 含 gate / model / trajectory；L3 含 map / method）
└── docs/                   # checkpoint 记录、AI 账本/日志、自评、贡献声明
```

## 报告中容易出错的两处（已修正，勿回退）

1. **L3 特征必须来自去平面趋势的图**。晶圆级平面梯度的极值必然落在图角；直接取全图极值会把角点当缺陷（坐标恰为 ±2.7，即 `np.linspace` 的端值）。管道已分离趋势与局域缺陷，并由 `reproduce.py` 的检查守住。
2. **L3 的 η 不能直接用 η₀**。η₀ 处残差是重复噪声的 12.8 倍（重建未拟合数据）；按差异原则取 η = 5.7e-2 η₀ 使残差 = 1.00 × 噪声。

## 关键数值（由管道生成，勿手改）

| 项目 | 值 |
|---|---|
| L1 修正因子 C(E_F,op) | 2.8672 |
| L1 修正载流子密度 | 3.727e11 cm⁻² |
| L1 修正迁移率 | 3.824e4 cm²/Vs |
| L2 模型 | cone（无能隙），E_g = 0 |
| L2 残差 | r_cone = 0.0140（指南 400 点网格）；去网格量化后 0.0058 = 噪声的 0.43 倍 |
| L2 费米轨迹 | −0.068 → +0.146 eV（中性点交叉 index 17→18）|
| L3 决策 | **fail（clear）**，max\|m\| = 0.0456 > 0.030 |
| L3 晶圆级梯度 | 6.03e-3 / 探针间距（x: −3.30e-3, y: −5.05e-3）|
| L3 局域特征 | 正 +0.0179 @ (+0.3, +1.5)；负 −0.0142 @ (−0.9, −0.9)（均在内部）|
| L3 η | 5.7e-2 × η₀（差异原则；η₀ 处残差 = 12.8 × 噪声）|
| L3 分辨率 | 1.80 探针间距 |
| L3 检测限 | 6.46e-5 |

## 随机种子

所有随机步骤（L2 bootstrap 200 次、L3 噪声 500 次）使用固定种子 `20260921`，保证逐位可复现。
